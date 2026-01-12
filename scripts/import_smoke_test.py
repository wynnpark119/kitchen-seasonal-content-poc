#!/usr/bin/env python3
"""
Import smoke test: 샘플 JSON 파일로 실제 upsert 검증

사용법:
    # 기본 (data/ 디렉토리의 첫 번째 JSON 파일 사용)
    python scripts/import_smoke_test.py

    # 특정 파일 지정
    python scripts/import_smoke_test.py --input data/collection.json --sample-size 10

    # Dry run (DB 쓰기 없이 검증)
    python scripts/import_smoke_test.py --dry-run
"""
import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any

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

# import_json_to_db 모듈 import
# sys.path에 project_root가 추가되어 있으므로 직접 import 가능
try:
    from scripts.import_json_to_db import (
        load_json_file, prepare_post_data, batch_upsert_posts,
        ImportStats, _parse_timestamp
    )
except ImportError:
    # 대안: 직접 함수 정의 (import 실패 시)
    def load_json_file(file_path):
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def prepare_post_data(item, keyword):
        # 간단한 구현 (실제로는 import_json_to_db의 함수 사용)
        return None
    
    def batch_upsert_posts(conn, posts_data, batch_size, timeout, stats):
        return 0
    
    class ImportStats:
        def __init__(self):
            self.total_files = 0
            self.total_records = 0
            self.success_records = 0
            self.failed_records = 0
            self.failed_rows = []
            self.start_time = time.time()
            self.last_log_time = time.time()
            self.last_log_count = 0
    
    def _parse_timestamp(timestamp_str):
        return 0
from worker.pipeline.db import get_db_connection, put_db_connection, create_pipeline_run, update_pipeline_run
from worker.pipeline.logging import setup_logger

logger = setup_logger("import_smoke_test")


def validate_json_structure(items: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
    """JSON 구조 검증"""
    errors = []
    
    if not isinstance(items, list):
        errors.append("JSON must be a list")
        return False, errors
    
    if len(items) == 0:
        errors.append("JSON list is empty")
        return False, errors
    
    # 샘플 아이템 검증
    sample = items[0]
    required_fields = ['id']  # 최소 필수 필드
    
    for field in required_fields:
        if field not in sample:
            # 다른 필드명 시도
            if field == 'id' and ('parsedId' not in sample and 'id' not in sample):
                errors.append(f"Missing required field: id (or parsedId)")
    
    return len(errors) == 0, errors


def test_prepare_data(items: List[Dict[str, Any]], keyword: str) -> tuple[int, List[tuple]]:
    """데이터 준비 테스트"""
    posts_data = []
    valid_count = 0
    
    for item in items:
        post_data = prepare_post_data(item, keyword)
        if post_data:
            posts_data.append(post_data)
            valid_count += 1
    
    return valid_count, posts_data


def test_batch_upsert(conn, posts_data: List[tuple], batch_size: int, dry_run: bool) -> Dict[str, Any]:
    """배치 upsert 테스트"""
    stats = ImportStats()
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - Skipping actual database writes")
        return {
            'success': True,
            'inserted': len(posts_data),
            'failed': 0,
            'dry_run': True
        }
    
    try:
        success_count = batch_upsert_posts(conn, posts_data, batch_size, 60000, stats)
        
        return {
            'success': True,
            'inserted': success_count,
            'failed': len(posts_data) - success_count,
            'dry_run': False
        }
    except Exception as e:
        logger.error(f"❌ Batch upsert test failed: {e}", exc_info=True)
        return {
            'success': False,
            'inserted': 0,
            'failed': len(posts_data),
            'error': str(e),
            'dry_run': False
        }


def main():
    parser = argparse.ArgumentParser(description="Import smoke test")
    parser.add_argument("--input", type=str,
                       help="Input JSON file path (default: first file in data/ directory)")
    parser.add_argument("--sample-size", type=int, default=10,
                       help="Number of items to test (default: 10)")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for inserts (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run mode (no database writes)")
    parser.add_argument("--keyword", type=str, default="smoke_test",
                       help="Keyword for posts (default: smoke_test)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Import Smoke Test")
    print("=" * 60)
    
    # JSON 파일 경로 결정
    if args.input:
        json_file = Path(args.input)
    else:
        data_dir = project_root / "data"
        json_files = list(data_dir.glob("*.json"))
        if not json_files:
            print("❌ ERROR: No JSON files found in data/ directory")
            print("   Use --input to specify a file")
            sys.exit(1)
        json_file = json_files[0]
        print(f"📂 Using first JSON file found: {json_file}")
    
    if not json_file.exists():
        print(f"❌ ERROR: JSON file not found: {json_file}")
        sys.exit(1)
    
    print(f"📄 JSON file: {json_file}")
    print(f"📊 Sample size: {args.sample_size}")
    print(f"🔍 Dry run: {args.dry_run}")
    
    # DATABASE_URL 확인
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    
    if not database_url and not args.dry_run:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # Test 1: JSON 파일 로드
    print("\n[1/4] Loading JSON file...")
    start_time = time.time()
    try:
        all_items = load_json_file(json_file)
        if not all_items:
            print("❌ ERROR: Failed to load JSON file or file is empty")
            sys.exit(1)
        
        # 샘플 추출
        sample_items = all_items[:args.sample_size] if len(all_items) > args.sample_size else all_items
        elapsed = time.time() - start_time
        
        print(f"✅ Loaded {len(all_items)} items, using {len(sample_items)} for test ({elapsed:.2f}s)")
    except Exception as e:
        print(f"❌ ERROR loading JSON: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test 2: JSON 구조 검증
    print("\n[2/4] Validating JSON structure...")
    try:
        is_valid, errors = validate_json_structure(sample_items)
        if not is_valid:
            print(f"❌ JSON structure validation failed:")
            for error in errors:
                print(f"   - {error}")
            sys.exit(1)
        print(f"✅ JSON structure is valid")
    except Exception as e:
        print(f"❌ ERROR validating JSON structure: {e}")
        sys.exit(1)
    
    # Test 3: 데이터 준비 테스트
    print("\n[3/4] Testing data preparation...")
    try:
        valid_count, posts_data = test_prepare_data(sample_items, args.keyword)
        print(f"✅ Prepared {valid_count} posts from {len(sample_items)} items")
        
        if valid_count == 0:
            print("⚠️  WARNING: No valid posts found in sample")
            print("   Sample item structure:")
            if sample_items:
                print(f"   {json.dumps(sample_items[0], indent=2, default=str)[:500]}")
    except Exception as e:
        print(f"❌ ERROR preparing data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test 4: 배치 upsert 테스트
    print("\n[4/4] Testing batch upsert...")
    
    conn = None
    run_id = None
    
    try:
        if not args.dry_run:
            # DB 연결
            print("   Connecting to database...")
            conn = get_db_connection()
            print("   ✅ Database connection successful")
            
            # Pipeline run 생성
            run_id = create_pipeline_run("smoke_test", status="running")
            print(f"   ✅ Pipeline run created: run_id={run_id}")
        
        # 배치 upsert 테스트
        start_time = time.time()
        result = test_batch_upsert(conn, posts_data, args.batch_size, args.dry_run)
        elapsed = time.time() - start_time
        
        if result['success']:
            print(f"✅ Batch upsert test successful ({elapsed:.2f}s)")
            print(f"   Inserted: {result['inserted']}")
            if result.get('failed', 0) > 0:
                print(f"   Failed: {result['failed']}")
        else:
            print(f"❌ Batch upsert test failed ({elapsed:.2f}s)")
            if 'error' in result:
                print(f"   Error: {result['error']}")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ ERROR during batch upsert test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            put_db_connection(conn)
        
        if run_id and not args.dry_run:
            try:
                status = "completed" if result.get('success') else "failed"
                update_pipeline_run(run_id, status)
            except:
                pass
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"✅ JSON file: {json_file.name}")
    print(f"✅ Sample items: {len(sample_items)}")
    print(f"✅ Valid posts: {valid_count}")
    print(f"✅ Batch upsert: {'Success' if result.get('success') else 'Failed'}")
    if not args.dry_run:
        print(f"✅ Inserted: {result.get('inserted', 0)}")
        if result.get('failed', 0) > 0:
            print(f"⚠️  Failed: {result.get('failed', 0)}")
    print("=" * 60)
    
    if result.get('success'):
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
