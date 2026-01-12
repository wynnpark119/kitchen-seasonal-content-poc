#!/usr/bin/env python3
"""
재처리 배치 스크립트: 실패한 임베딩만 재생성

요구사항:
- 실패 대상만 재처리 (이미 성공한 것은 건드리지 않음)
- 안전한 embedding_text 생성 (토큰 제한 준수)
- 재시도 정책 (permanent/transient 에러 분류)
- DB 풀 고갈 방지
- 재실행/중단/재개 가능
- Idempotent (같은 데이터로 재실행해도 중복/오염 없음)
"""
import os
import sys
import argparse
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

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
        load_dotenv()  # 시스템 환경 변수만 로드
except ImportError:
    # dotenv가 없으면 .env 파일을 직접 읽기
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and not os.getenv(key):
                        os.environ[key] = value

from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError
import threading

from worker.pipeline.db import (
    get_db_connection, put_db_connection, upsert_embeddings_batch,
    create_pipeline_run, update_pipeline_run
)
from worker.pipeline.preprocess import (
    build_safe_embedding_text, get_text_hash, is_deleted_post, clean_text
)
from worker.pipeline.config import (
    EMBEDDING_MODEL, EMBEDDING_DIM, API_MAX_RETRIES, API_BACKOFF_FACTOR,
    EMBEDDING_BATCH_SIZE, DB_WRITE_CONCURRENCY
)
from worker.pipeline.logging import setup_logger

logger = setup_logger("retry_embeddings")

# DB write 동시성 제한
db_write_semaphore = threading.Semaphore(DB_WRITE_CONCURRENCY)

# Maximum tokens for text-embedding-3-large
MAX_TOKENS = 8192

# 재시도 정책: Permanent 에러 (재시도 금지)
PERMANENT_ERROR_CODES = {
    'invalid_request_error',  # 토큰 초과, 잘못된 입력 등
    'context_length_exceeded',  # 컨텍스트 길이 초과
}

# 재시도 정책: Transient 에러 (재시도 허용)
TRANSIENT_ERROR_CODES = {
    'rate_limit_error',  # 429
    'server_error',  # 5xx
    'timeout_error',  # 타임아웃
}


def is_permanent_error(error: Exception) -> bool:
    """Permanent 에러인지 판단 (재시도 금지)"""
    if isinstance(error, APIError):
        error_code = getattr(error, 'code', None) or str(error.type) if hasattr(error, 'type') else None
        if error_code:
            error_code_lower = error_code.lower()
            for perm_code in PERMANENT_ERROR_CODES:
                if perm_code in error_code_lower:
                    return True
        
        # 400 Bad Request는 일반적으로 permanent
        if hasattr(error, 'status_code') and error.status_code == 400:
            return True
    
    # 토큰/길이 관련 에러 메시지 체크
    error_msg = str(error).lower()
    if any(keyword in error_msg for keyword in ['token', 'length', 'too long', 'exceeded', 'invalid request']):
        return True
    
    return False


def is_transient_error(error: Exception) -> bool:
    """Transient 에러인지 판단 (재시도 허용)"""
    if isinstance(error, RateLimitError):
        return True
    
    if isinstance(error, APIConnectionError) or isinstance(error, APITimeoutError):
        return True
    
    if isinstance(error, APIError):
        error_code = getattr(error, 'code', None) or str(error.type) if hasattr(error, 'type') else None
        if error_code:
            error_code_lower = error_code.lower()
            for trans_code in TRANSIENT_ERROR_CODES:
                if trans_code in error_code_lower:
                    return True
        
        # 5xx는 transient
        if hasattr(error, 'status_code') and error.status_code and 500 <= error.status_code < 600:
            return True
    
    return False


def get_failed_posts(
    run_id: Optional[int] = None,
    since: Optional[datetime] = None,
    limit: Optional[int] = None,
    only_status: Optional[str] = None
) -> List[Tuple[str, str, Optional[str], Optional[List[Dict]], Optional[List[str]]]]:
    """
    실패한 포스트 조회
    
    실패 판단 기준:
    - 특정 run_id에 대해 임베딩이 없는 포스트
    - 또는 모든 포스트 중 임베딩이 없는 것들
    
    Args:
        run_id: 특정 run_id에 대해 실패한 것만 조회 (None이면 모든 포스트)
        since: 특정 시점 이후의 포스트만 조회
        limit: 최대 조회 개수
        only_status: 'failed' 또는 'null' (현재는 사용하지 않음, 향후 확장용)
    
    Returns:
        List of (post_id, title, body, comments, serp_snippets) tuples
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 기본 쿼리: 임베딩이 없는 포스트
            if run_id:
                # 특정 run_id에 대해 임베딩이 없는 포스트
                query = """
                    SELECT DISTINCT rp.reddit_post_id, rp.title, rp.body, rp.upvotes, rp.num_comments
                    FROM raw_reddit_posts rp
                    WHERE NOT EXISTS (
                        SELECT 1 FROM embeddings e
                        WHERE e.doc_type = 'reddit_post'
                        AND e.doc_id = rp.reddit_post_id
                        AND e.created_from_run_id = %s
                    )
                    AND rp.title IS NOT NULL
                    AND LENGTH(COALESCE(rp.title, '')) > 0
                """
                params = [run_id]
            else:
                # 모든 포스트 중 임베딩이 없는 것들 (최신 run_id 기준)
                query = """
                    SELECT DISTINCT rp.reddit_post_id, rp.title, rp.body, rp.upvotes, rp.num_comments
                    FROM raw_reddit_posts rp
                    WHERE NOT EXISTS (
                        SELECT 1 FROM embeddings e
                        WHERE e.doc_type = 'reddit_post'
                        AND e.doc_id = rp.reddit_post_id
                    )
                    AND rp.title IS NOT NULL
                    AND LENGTH(COALESCE(rp.title, '')) > 0
                """
                params = []
            
            # since 조건 추가
            if since:
                query += " AND rp.created_at >= %s"
                params.append(since)
            
            query += " ORDER BY rp.upvotes DESC, rp.num_comments DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query, params)
            posts = cur.fetchall()
            
            # 댓글 및 SERP 데이터 조회 (선택적)
            result = []
            for post_id, title, body, upvotes, num_comments in posts:
                # 댓글 조회 (상위 5개)
                cur.execute("""
                    SELECT body, upvotes
                    FROM raw_reddit_comments
                    WHERE reddit_post_id = %s
                    ORDER BY upvotes DESC, is_top DESC
                    LIMIT 5
                """, (post_id,))
                comments = [{'body': row[0], 'upvotes': row[1]} for row in cur.fetchall()]
                
                # SERP 스니펫 조회 (선택적, 현재는 스킵)
                serp_snippets = None
                
                result.append((post_id, title, body, comments if comments else None, serp_snippets))
            
            return result
    finally:
        if conn:
            put_db_connection(conn)


def generate_embeddings_batch_with_retry(
    texts: List[str],
    client: OpenAI,
    max_retries: int = 3
) -> Tuple[List[Optional[List[float]]], List[int]]:
    """
    배치로 임베딩 생성 (재시도 정책 포함)
    
    Returns:
        (embeddings, failed_indices) 튜플
        - embeddings: 성공한 임베딩 리스트 (None으로 채워짐)
        - failed_indices: 실패한 인덱스 리스트
    """
    embeddings: List[Optional[List[float]]] = [None] * len(texts)
    failed_indices: List[int] = []
    
    for attempt in range(max_retries):
        if attempt > 0 and not failed_indices:
            # 모든 텍스트가 성공했으면 종료
            break
        
        # 재시도할 텍스트들
        if attempt == 0:
            texts_to_process = texts
            indices_to_process = list(range(len(texts)))
        else:
            texts_to_process = [texts[i] for i in failed_indices]
            indices_to_process = failed_indices.copy()
            failed_indices = []  # 재시도 리스트 초기화
        
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts_to_process
            )
            
            # 성공한 임베딩 저장
            for i, item in enumerate(response.data):
                if i < len(indices_to_process):
                    original_idx = indices_to_process[i]
                    embeddings[original_idx] = item.embedding
            
            # 모든 텍스트가 성공했는지 확인
            if None not in embeddings:
                break
            else:
                # 실패한 인덱스 수집
                for idx in indices_to_process:
                    if embeddings[idx] is None:
                        failed_indices.append(idx)
                
                # Permanent 에러가 아니면 재시도
                if attempt < max_retries - 1:
                    continue
                else:
                    break
                
        except Exception as e:
            # Permanent 에러는 즉시 실패 처리
            if is_permanent_error(e):
                logger.error(f"Permanent error in batch embedding (no retry): {e}")
                # 실패한 인덱스들을 failed_indices에 추가
                for idx in indices_to_process:
                    if embeddings[idx] is None:
                        failed_indices.append(idx)
                break
            
            # Transient 에러는 재시도
            if is_transient_error(e) and attempt < max_retries - 1:
                wait_time = (API_BACKOFF_FACTOR ** attempt) + random.uniform(0, 1)  # jitter 추가
                logger.warning(f"Transient error in batch embedding (attempt {attempt + 1}/{max_retries}), retrying in {wait_time:.2f}s: {e}")
                time.sleep(wait_time)
                # 재시도할 인덱스 유지
                failed_indices = indices_to_process.copy()
                continue
            else:
                # 최대 재시도 횟수 초과 또는 알 수 없는 에러
                logger.error(f"Failed to generate batch embeddings after {attempt + 1} attempts: {e}")
                # 실패한 인덱스들을 failed_indices에 추가
                for idx in indices_to_process:
                    if embeddings[idx] is None:
                        failed_indices.append(idx)
                break
    
    return embeddings, failed_indices


def process_failed_embeddings(
    run_id: int,
    dry_run: bool = False,
    limit: Optional[int] = None,
    since: Optional[datetime] = None,
    batch_size: int = EMBEDDING_BATCH_SIZE,
    embed_concurrency: int = 5,
    db_write_concurrency: int = DB_WRITE_CONCURRENCY
) -> Dict[str, Any]:
    """
    실패한 임베딩 재처리
    
    Args:
        run_id: Pipeline run ID (새로운 run_id 생성 또는 기존 사용)
        dry_run: Dry run mode
        limit: 최대 처리 개수
        since: 특정 시점 이후만 처리
        batch_size: Embedding API 배치 크기
        embed_concurrency: Embedding API 동시 호출 수
        db_write_concurrency: DB write 동시성 제한
    
    Returns:
        Statistics dictionary
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key and not dry_run:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    if not dry_run:
        client = OpenAI(api_key=openai_key)
    
    stats = {
        "total_failed": 0,
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped_deleted": 0,
        "skipped_too_short": 0,
        "permanent_errors": 0,
        "transient_errors": 0,
        "start_time": time.time(),
        "errors": []
    }
    
    # 실패한 포스트 조회
    logger.info(f"Fetching failed posts (run_id={run_id}, limit={limit}, since={since})...")
    failed_posts = get_failed_posts(run_id=run_id, since=since, limit=limit)
    stats["total_failed"] = len(failed_posts)
    
    logger.info(f"Found {stats['total_failed']} failed posts to retry")
    
    if stats["total_failed"] == 0:
        logger.info("No failed posts to retry")
        return stats
    
    # 안전한 embedding_text 생성 및 배치 처리
    posts_to_process = []
    for post_id, title, body, comments, serp_snippets in failed_posts:
        try:
            # 삭제된 글 스킵
            if is_deleted_post(title, body):
                stats["skipped_deleted"] += 1
                continue
            
            # 안전한 embedding_text 생성
            embedding_text = build_safe_embedding_text(
                title=title,
                body=body,
                comments=comments,
                serp_snippets=serp_snippets,
                max_tokens=MAX_TOKENS
            )
            
            # 너무 짧은 글 스킵
            if len(embedding_text) < 30:
                stats["skipped_too_short"] += 1
                continue
            
            # text_hash 생성
            text_hash = get_text_hash(embedding_text)
            
            posts_to_process.append((post_id, embedding_text, text_hash))
        except Exception as e:
            logger.error(f"Error preprocessing post {post_id}: {e}")
            stats["errors"].append(f"preprocess_{post_id}: {str(e)}")
            stats["failed"] += 1
    
    logger.info(f"Processing {len(posts_to_process)} posts (skipped {stats['skipped_deleted'] + stats['skipped_too_short']})")
    
    # 배치 처리
    batch = []
    batch_post_ids = []
    batch_text_hashes = []
    processed_count = 0
    
    for post_id, embedding_text, text_hash in posts_to_process:
        batch.append(embedding_text)
        batch_post_ids.append(post_id)
        batch_text_hashes.append(text_hash)
        
        # 배치가 가득 차면 처리
        if len(batch) >= batch_size:
            if dry_run:
                logger.info(f"[DRY RUN] Would generate embeddings for batch of {len(batch)} posts")
                stats["success"] += len(batch)
                stats["processed"] += len(batch)
            else:
                # API 호출 (DB 커넥션 없음)
                batch_start_time = time.time()
                embeddings, failed_indices = generate_embeddings_batch_with_retry(batch, client)
                api_time = time.time() - batch_start_time
                
                # 성공한 임베딩만 DB에 저장
                successful_data = []
                for post_id, text_hash, embedding in zip(batch_post_ids, batch_text_hashes, embeddings):
                    if embedding is not None:
                        successful_data.append((
                            "reddit_post", post_id, embedding, text_hash,
                            EMBEDDING_MODEL, EMBEDDING_DIM, run_id
                        ))
                    else:
                        stats["failed"] += 1
                        stats["errors"].append(f"embedding_failed_{post_id}")
                
                # DB 저장 (동시성 제한)
                if successful_data:
                    db_save_start = time.time()
                    with db_write_semaphore:
                        upsert_embeddings_batch(successful_data, run_id)
                    db_save_time = time.time() - db_save_start
                    
                    stats["success"] += len(successful_data)
                    stats["processed"] += len(successful_data)
                    
                    logger.info(f"[PROGRESS] Batch: {len(successful_data)}/{len(batch)} success | "
                              f"Total: {stats['processed']}/{len(posts_to_process)} | "
                              f"API: {api_time:.2f}s | DB: {db_save_time:.2f}s")
                else:
                    logger.warning(f"[PROGRESS] Batch: 0/{len(batch)} success (all failed)")
            
            # 배치 초기화
            processed_count += len(batch_post_ids)
            batch = []
            batch_post_ids = []
            batch_text_hashes = []
    
    # 남은 배치 처리
    if batch:
        if dry_run:
            logger.info(f"[DRY RUN] Would generate embeddings for final batch of {len(batch)} posts")
            stats["success"] += len(batch)
            stats["processed"] += len(batch)
        else:
            batch_start_time = time.time()
            embeddings, failed_indices = generate_embeddings_batch_with_retry(batch, client)
            api_time = time.time() - batch_start_time
            
            successful_data = []
            for post_id, text_hash, embedding in zip(batch_post_ids, batch_text_hashes, embeddings):
                if embedding is not None:
                    successful_data.append((
                        "reddit_post", post_id, embedding, text_hash,
                        EMBEDDING_MODEL, EMBEDDING_DIM, run_id
                    ))
                else:
                    stats["failed"] += 1
                    stats["errors"].append(f"embedding_failed_{post_id}")
            
            if successful_data:
                db_save_start = time.time()
                with db_write_semaphore:
                    upsert_embeddings_batch(successful_data, run_id)
                db_save_time = time.time() - db_save_start
                
                stats["success"] += len(successful_data)
                stats["processed"] += len(successful_data)
                
                logger.info(f"[PROGRESS] Final batch: {len(successful_data)}/{len(batch)} success | "
                          f"Total: {stats['processed']}/{len(posts_to_process)} | "
                          f"API: {api_time:.2f}s | DB: {db_save_time:.2f}s")
    
    elapsed_time = time.time() - stats["start_time"]
    stats["elapsed_time"] = elapsed_time
    
    logger.info(f"Retry completed:")
    logger.info(f"  Total failed: {stats['total_failed']}")
    logger.info(f"  Processed: {stats['processed']}")
    logger.info(f"  Success: {stats['success']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"  Skipped (deleted): {stats['skipped_deleted']}")
    logger.info(f"  Skipped (too short): {stats['skipped_too_short']}")
    logger.info(f"  Elapsed time: {elapsed_time:.2f}s")
    logger.info(f"  Processing rate: {stats['processed']/elapsed_time:.1f} posts/s" if elapsed_time > 0 else "N/A")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Retry failed embeddings")
    parser.add_argument("--run-id", type=int, help="Pipeline run ID (default: create new)")
    parser.add_argument("--limit", type=int, default=500, help="Maximum posts to process (default: 500)")
    parser.add_argument("--since", type=str, help="Only process posts created after this date (ISO format: YYYY-MM-DD)")
    parser.add_argument("--only-status", type=str, choices=['failed', 'null'], help="Filter by status (not used currently)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no DB writes)")
    parser.add_argument("--batch-size", type=int, default=EMBEDDING_BATCH_SIZE, help=f"Embedding batch size (default: {EMBEDDING_BATCH_SIZE})")
    parser.add_argument("--embed-concurrency", type=int, default=5, help="Embedding API concurrency (default: 5)")
    parser.add_argument("--db-write-concurrency", type=int, default=DB_WRITE_CONCURRENCY, help=f"DB write concurrency (default: {DB_WRITE_CONCURRENCY})")
    
    args = parser.parse_args()
    
    # Run ID 처리
    if args.run_id:
        run_id = args.run_id
        logger.info(f"Using existing run_id: {run_id}")
    else:
        run_id = create_pipeline_run("retry_failed_embeddings", "running")
        logger.info(f"Created new run_id: {run_id}")
    
    # Since 날짜 파싱
    since = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since)
        except ValueError:
            logger.error(f"Invalid date format: {args.since}. Use ISO format: YYYY-MM-DD")
            sys.exit(1)
    
    try:
        stats = process_failed_embeddings(
            run_id=run_id,
            dry_run=args.dry_run,
            limit=args.limit,
            since=since,
            batch_size=args.batch_size,
            embed_concurrency=args.embed_concurrency,
            db_write_concurrency=args.db_write_concurrency
        )
        
        # Run 상태 업데이트
        if not args.dry_run:
            if stats["failed"] == 0:
                update_pipeline_run(run_id, "completed", metadata=stats)
            else:
                update_pipeline_run(run_id, "completed", error_message=f"{stats['failed']} posts failed", metadata=stats)
        
        logger.info("✅ Retry process completed successfully")
        return 0
    except Exception as e:
        logger.error(f"❌ Retry process failed: {e}", exc_info=True)
        if not args.dry_run and args.run_id:
            update_pipeline_run(run_id, "failed", error_message=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
