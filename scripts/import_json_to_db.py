#!/usr/bin/env python3
"""
JSON 파일을 Postgres에 안정적으로 적재하는 스크립트

필수 기능:
- 타임아웃 설정 (connect, statement, pool acquire)
- 진행률 로그 (N건마다)
- 배치 처리 (batch insert/upsert)
- 오류 격리 (실패 row는 별도 기록, 전체 중단 방지)
- Idempotent upsert (UNIQUE 키 기반)

사용법:
    # 단일 파일
    python scripts/import_json_to_db.py --input s3://bucket/key.json --batch-size 500

    # 디렉토리
    python scripts/import_json_to_db.py --input /data/imports/2024-01-15 --batch-size 500

    # URI 리스트
    python scripts/import_json_to_db.py --input-uris uploaded_uris_job123.txt --batch-size 500

    # Dry run
    python scripts/import_json_to_db.py --input data.json --dry-run

환경 변수:
    DATABASE_URL: PostgreSQL connection string
    CONNECT_TIMEOUT: Connection timeout in seconds (default: 10)
    STATEMENT_TIMEOUT: Statement timeout in milliseconds (default: 60000)
"""
import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

import psycopg2
from psycopg2.extras import execute_batch, Json
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import pool

# 프로젝트 모듈 import
from worker.pipeline.db import get_db_connection, put_db_connection, create_pipeline_run, update_pipeline_run
from worker.pipeline.logging import setup_logger

logger = setup_logger("import_json_to_db")


class ImportStats:
    """Import 통계 추적"""
    def __init__(self):
        self.total_files = 0
        self.total_records = 0
        self.success_records = 0
        self.failed_records = 0
        self.failed_rows = []
        self.start_time = time.time()
        self.last_log_time = time.time()
        self.last_log_count = 0
    
    def add_success(self, count: int = 1):
        self.success_records += count
        self.total_records += count
    
    def add_failure(self, row_data: Dict[str, Any], error: str):
        self.failed_records += 1
        self.total_records += 1
        self.failed_rows.append({
            'data': row_data,
            'error': str(error)
        })
    
    def get_elapsed(self) -> float:
        return time.time() - self.start_time
    
    def get_rate(self) -> float:
        elapsed = self.get_elapsed()
        return self.success_records / elapsed if elapsed > 0 else 0.0


def download_from_s3(bucket: str, key: str, local_path: Path,
                     access_key: str, secret_key: str, endpoint_url: Optional[str] = None) -> Path:
    """S3/R2에서 파일 다운로드"""
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        logger.error("boto3 not installed. Run: pip install boto3")
        sys.exit(1)
    
    logger.info(f"📥 Downloading from S3/R2: s3://{bucket}/{key}")
    
    s3_config = {
        'aws_access_key_id': access_key,
        'aws_secret_access_key': secret_key,
    }
    
    if endpoint_url:
        s3_config['endpoint_url'] = endpoint_url
        s3_config['region_name'] = 'auto'
    
    s3_client = boto3.client('s3', **s3_config)
    
    try:
        start_time = time.time()
        s3_client.download_file(bucket, key, str(local_path))
        elapsed = time.time() - start_time
        file_size = local_path.stat().st_size
        logger.info(f"✅ Download successful ({elapsed:.2f}s, {file_size / 1024 / 1024:.2f} MB)")
        return local_path
    except ClientError as e:
        logger.error(f"❌ Download failed: {e}")
        raise


def download_from_gcs(bucket: str, blob_name: str, local_path: Path,
                      credentials_path: Optional[str] = None) -> Path:
    """GCS에서 파일 다운로드"""
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
    except ImportError:
        logger.error("google-cloud-storage not installed. Run: pip install google-cloud-storage")
        sys.exit(1)
    
    logger.info(f"📥 Downloading from GCS: gs://{bucket}/{blob_name}")
    
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        storage_client = storage.Client(credentials=credentials)
    else:
        storage_client = storage.Client()
    
    try:
        bucket_obj = storage_client.bucket(bucket)
        blob = bucket_obj.blob(blob_name)
        
        start_time = time.time()
        blob.download_to_filename(str(local_path))
        elapsed = time.time() - start_time
        file_size = local_path.stat().st_size
        logger.info(f"✅ Download successful ({elapsed:.2f}s, {file_size / 1024 / 1024:.2f} MB)")
        return local_path
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        raise


def resolve_file_path(uri_or_path: str, temp_dir: Path) -> Path:
    """URI 또는 로컬 경로를 로컬 파일 경로로 변환"""
    if uri_or_path.startswith("s3://"):
        # S3 URI 파싱
        parts = uri_or_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        local_path = temp_dir / Path(key).name
        
        access_key = os.getenv("STORAGE_ACCESS_KEY")
        secret_key = os.getenv("STORAGE_SECRET_KEY")
        endpoint_url = os.getenv("STORAGE_ENDPOINT_URL")
        
        if not access_key or not secret_key:
            logger.error("STORAGE_ACCESS_KEY and STORAGE_SECRET_KEY required for S3 download")
            sys.exit(1)
        
        return download_from_s3(bucket, key, local_path, access_key, secret_key, endpoint_url)
    
    elif uri_or_path.startswith("gs://"):
        # GCS URI 파싱
        parts = uri_or_path.replace("gs://", "").split("/", 1)
        bucket = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""
        
        local_path = temp_dir / Path(blob_name).name
        
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        return download_from_gcs(bucket, blob_name, local_path, credentials_path)
    
    elif uri_or_path.startswith("file://"):
        # 로컬 파일 경로
        return Path(uri_or_path.replace("file://", ""))
    
    else:
        # 로컬 경로로 간주
        return Path(uri_or_path)


def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """JSON 파일 로드"""
    logger.info(f"📂 Loading JSON file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.error(f"JSON file must contain a list, got {type(data)}")
            return []
        
        logger.info(f"✅ Loaded {len(data)} items from {file_path.name}")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to load JSON file: {e}")
        return []


def prepare_post_data(item: Dict[str, Any], keyword: str) -> Optional[tuple]:
    """Reddit post 데이터를 DB insert용 튜플로 변환"""
    try:
        # process_apify_results.py와 동일한 로직
        data_type = item.get('dataType') or item.get('kind', 'post')
        
        if data_type != 'post':
            return None
        
        post_id = item.get('parsedId') or item.get('id', '')
        if not post_id or not isinstance(post_id, str) or len(str(post_id).strip()) == 0:
            return None
        
        post_id = str(post_id).strip()
        
        subreddit = item.get('subredditName') or item.get('subreddit', '')
        if not subreddit:
            community = item.get('communityName', '')
            if community:
                subreddit = community.replace('r/', '')
        
        created_utc_str = item.get('createdAt') or item.get('created_utc', '')
        created_utc = _parse_timestamp(created_utc_str)
        if created_utc <= 0:
            created_utc = int(time.time())
        
        return (
            post_id,
            (subreddit or 'unknown')[:100],
            (item.get('title', '') or 'Untitled')[:10000],
            (item.get('body') or item.get('text') or item.get('selftext', '') or '')[:50000] or None,
            (item.get('authorName') or item.get('author', '') or '')[:100] or None,
            created_utc,
            max(0, int(item.get('upVotes') or item.get('upvotes') or item.get('score', 0))),
            max(0, int(item.get('commentsCount') or item.get('num_comments', 0))),
            (item.get('postUrl') or item.get('permalink') or item.get('url', '') or '')[:5000] or None,
            (item.get('contentUrl') or item.get('postUrl') or item.get('url', '') or '')[:5000] or None,
            keyword[:200],
            Json(item)
        )
    except Exception as e:
        logger.debug(f"Error preparing post data: {e}")
        return None


def _parse_timestamp(timestamp_str: str) -> int:
    """Parse ISO timestamp to Unix timestamp"""
    if not timestamp_str:
        return 0
    
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except:
        return 0


def batch_upsert_posts(conn, posts_data: List[tuple], batch_size: int, 
                      statement_timeout_ms: int, stats: ImportStats) -> int:
    """배치로 posts를 upsert"""
    if not posts_data:
        return 0
    
    success_count = 0
    
    # 배치 단위로 처리
    for i in range(0, len(posts_data), batch_size):
        batch = posts_data[i:i + batch_size]
        
        try:
            cur = conn.cursor()
            
            # Statement timeout 설정
            cur.execute(f"SET statement_timeout = {statement_timeout_ms}")
            
            # 배치 upsert 실행
            execute_batch(cur, """
                INSERT INTO raw_reddit_posts (
                    reddit_post_id, subreddit, title, body, author,
                    created_utc, upvotes, num_comments, permalink, url,
                    keyword, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reddit_post_id) DO UPDATE SET
                    upvotes = EXCLUDED.upvotes,
                    num_comments = EXCLUDED.num_comments,
                    updated_at = CURRENT_TIMESTAMP
            """, batch, page_size=min(100, batch_size))
            
            conn.commit()
            success_count += len(batch)
            
        except psycopg2.extensions.QueryCanceledError:
            logger.error(f"❌ Query timeout (statement_timeout exceeded) for batch {i//batch_size + 1}")
            conn.rollback()
            # 타임아웃된 배치는 실패로 기록
            for row in batch:
                stats.add_failure({'post_id': row[0]}, "Query timeout")
        except Exception as e:
            logger.error(f"❌ Batch upsert error for batch {i//batch_size + 1}: {e}")
            conn.rollback()
            # 실패한 배치의 각 row를 개별적으로 기록
            for row in batch:
                try:
                    # 개별 upsert 시도
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO raw_reddit_posts (
                            reddit_post_id, subreddit, title, body, author,
                            created_utc, upvotes, num_comments, permalink, url,
                            keyword, raw_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (reddit_post_id) DO UPDATE SET
                            upvotes = EXCLUDED.upvotes,
                            num_comments = EXCLUDED.num_comments,
                            updated_at = CURRENT_TIMESTAMP
                    """, row)
                    conn.commit()
                    success_count += 1
                except Exception as row_error:
                    stats.add_failure({'post_id': row[0]}, str(row_error))
        finally:
            if 'cur' in locals():
                cur.close()
    
    return success_count


def process_file(file_path: Path, keyword: str, run_id: int, batch_size: int,
                statement_timeout_ms: int, max_errors: int, stats: ImportStats, dry_run: bool) -> bool:
    """단일 JSON 파일 처리"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing file: {file_path.name}")
    logger.info(f"{'='*60}")
    
    # JSON 로드
    items = load_json_file(file_path)
    if not items:
        logger.warning(f"⚠️  No items found in {file_path.name}")
        return False
    
    # 키워드 추출 (파일명에서 또는 기본값)
    if not keyword:
        # 파일명에서 키워드 추출 시도
        keyword = file_path.stem.replace('_', ' ').replace('-', ' ')
    
    logger.info(f"Keyword: {keyword}")
    logger.info(f"Total items: {len(items)}")
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No database writes")
        return True
    
    # 데이터 준비
    posts_data = []
    for item in items:
        post_data = prepare_post_data(item, keyword)
        if post_data:
            posts_data.append(post_data)
    
    logger.info(f"Prepared {len(posts_data)} posts for insertion")
    
    if not posts_data:
        logger.warning("⚠️  No valid posts found")
        return False
    
    # DB 연결
    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error(f"❌ Failed to get DB connection: {e}")
        return False
    
    try:
        # 배치 upsert
        success_count = batch_upsert_posts(conn, posts_data, batch_size, 
                                          statement_timeout_ms, stats)
        
        stats.add_success(success_count)
        
        logger.info(f"✅ Successfully inserted {success_count} posts")
        
        # max_errors 체크
        if stats.failed_records > max_errors:
            logger.error(f"❌ Too many errors ({stats.failed_records} > {max_errors}), stopping")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error processing file: {e}", exc_info=True)
        return False
    finally:
        put_db_connection(conn)


def log_progress(stats: ImportStats, progress_interval: int = 100):
    """진행률 로그 출력"""
    elapsed = stats.get_elapsed()
    
    if stats.total_records % progress_interval == 0 or elapsed - stats.last_log_time > 10:
        rate = stats.get_rate()
        logger.info(
            f"[PROGRESS] Records: {stats.success_records}/{stats.total_records} "
            f"(Success: {stats.success_records}, Failed: {stats.failed_records}) | "
            f"Elapsed: {elapsed:.1f}s | Rate: {rate:.1f} records/s"
        )
        stats.last_log_time = elapsed


def main():
    parser = argparse.ArgumentParser(description="Import JSON files to PostgreSQL")
    parser.add_argument("--input", type=str,
                       help="Input JSON file or directory path")
    parser.add_argument("--input-uris", type=str,
                       help="File containing list of URIs (one per line)")
    parser.add_argument("--batch-size", type=int, default=500,
                       help="Batch size for inserts (default: 500)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run mode (no database writes)")
    parser.add_argument("--max-errors", type=int, default=1000,
                       help="Maximum errors before stopping (default: 1000)")
    parser.add_argument("--job-id", type=str, default=None,
                       help="Job ID for tracking (default: auto-generated)")
    parser.add_argument("--keyword", type=str, default="",
                       help="Keyword for posts (default: extracted from filename)")
    parser.add_argument("--connect-timeout", type=int, default=10,
                       help="Connection timeout in seconds (default: 10)")
    parser.add_argument("--statement-timeout", type=int, default=60000,
                       help="Statement timeout in milliseconds (default: 60000)")
    
    args = parser.parse_args()
    
    # Job ID 생성
    job_id = args.job_id or f"import-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # DATABASE_URL 확인
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    
    if not database_url and not args.dry_run:
        logger.error("❌ DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # DB 연결 정보 로깅 (민감 정보 마스킹)
    if database_url:
        url_parts = database_url.split('@')
        if len(url_parts) > 1:
            masked_url = f"...@{url_parts[-1]}"
        else:
            masked_url = database_url[:50] + "..."
        logger.info(f"📊 Database: {masked_url}")
    
    # Pipeline run 생성
    run_id = None
    if not args.dry_run:
        try:
            run_id = create_pipeline_run("import", status="running")
            logger.info(f"📝 Pipeline run created: run_id={run_id}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to create pipeline run: {e}")
    
    # 입력 파일/URI 목록 결정
    input_files = []
    
    if args.input_uris:
        # URI 리스트 파일 읽기
        uri_file = Path(args.input_uris)
        if not uri_file.exists():
            logger.error(f"❌ URI list file not found: {uri_file}")
            sys.exit(1)
        
        with open(uri_file, 'r') as f:
            uris = [line.strip() for line in f if line.strip()]
        
        logger.info(f"📋 Found {len(uris)} URIs in list file")
        
        # 임시 디렉토리 생성
        temp_dir = project_root / "temp_imports"
        temp_dir.mkdir(exist_ok=True)
        
        # URI를 로컬 파일로 변환
        for uri in uris:
            try:
                local_path = resolve_file_path(uri, temp_dir)
                input_files.append(local_path)
            except Exception as e:
                logger.error(f"❌ Failed to resolve URI {uri}: {e}")
    
    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"❌ Input path not found: {input_path}")
            sys.exit(1)
        
        if input_path.is_file():
            input_files = [input_path]
        elif input_path.is_dir():
            input_files = list(input_path.glob("*.json"))
            if not input_files:
                logger.error(f"❌ No JSON files found in {input_path}")
                sys.exit(1)
        else:
            logger.error(f"❌ Invalid input path: {input_path}")
            sys.exit(1)
    else:
        logger.error("❌ --input or --input-uris required")
        sys.exit(1)
    
    logger.info(f"📂 Found {len(input_files)} files to process")
    
    # 통계 초기화
    stats = ImportStats()
    stats.total_files = len(input_files)
    
    # 시작 로그
    logger.info("=" * 60)
    logger.info("JSON Import to Database")
    logger.info("=" * 60)
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Files: {len(input_files)}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Max errors: {args.max_errors}")
    logger.info(f"Statement timeout: {args.statement_timeout}ms")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)
    
    # 각 파일 처리
    for file_path in input_files:
        success = process_file(
            file_path, args.keyword, run_id, args.batch_size,
            args.statement_timeout, args.max_errors, stats, args.dry_run
        )
        
        if not success:
            logger.warning(f"⚠️  Failed to process {file_path.name}")
        
        # 진행률 로그
        log_progress(stats, progress_interval=100)
        
        # max_errors 체크
        if stats.failed_records > args.max_errors:
            logger.error(f"❌ Stopping due to too many errors ({stats.failed_records} > {args.max_errors})")
            break
    
    # 최종 통계
    total_elapsed = stats.get_elapsed()
    final_rate = stats.get_rate()
    
    logger.info("\n" + "=" * 60)
    logger.info("Import Summary")
    logger.info("=" * 60)
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Files processed: {stats.total_files}")
    logger.info(f"Total records: {stats.total_records}")
    logger.info(f"Success: {stats.success_records}")
    logger.info(f"Failed: {stats.failed_records}")
    logger.info(f"Total time: {total_elapsed:.2f}s")
    logger.info(f"Average rate: {final_rate:.2f} records/s")
    
    # 실패 샘플 출력 (최대 10개)
    if stats.failed_rows:
        logger.info(f"\n⚠️  Failed rows (showing up to 10):")
        for i, failed_row in enumerate(stats.failed_rows[:10], 1):
            logger.info(f"  {i}. {failed_row.get('data', {}).get('post_id', 'unknown')}: {failed_row.get('error', 'unknown error')}")
    
    logger.info("=" * 60)
    
    # Pipeline run 업데이트
    if run_id:
        try:
            status = "completed" if stats.failed_records == 0 else "completed_with_errors"
            metadata = {
                'total_files': stats.total_files,
                'total_records': stats.total_records,
                'success_records': stats.success_records,
                'failed_records': stats.failed_records,
                'elapsed_seconds': total_elapsed,
                'rate_per_second': final_rate
            }
            update_pipeline_run(run_id, status, metadata=metadata)
        except Exception as e:
            logger.warning(f"⚠️  Failed to update pipeline run: {e}")
    
    # 실패한 row를 파일로 저장
    if stats.failed_rows:
        failed_file = project_root / f"failed_rows_{job_id}.json"
        with open(failed_file, 'w') as f:
            json.dump(stats.failed_rows, f, indent=2, default=str)
        logger.info(f"📄 Failed rows saved to: {failed_file}")
    
    # 종료 코드
    if stats.failed_records > args.max_errors:
        sys.exit(1)
    elif stats.failed_records > 0:
        sys.exit(2)  # 부분 실패
    else:
        sys.exit(0)  # 성공


if __name__ == "__main__":
    main()
