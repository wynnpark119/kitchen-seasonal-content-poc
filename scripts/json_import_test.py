#!/usr/bin/env python3
"""
JSON import test: 샘플 JSON 파일로 배치 insert/upsert 테스트

사용법:
    export DATABASE_URL="postgresql://..."
    python scripts/json_import_test.py [--json-file PATH] [--sample-size N]
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

from worker.pipeline.db import get_db_connection, put_db_connection, create_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("json_import_test")

def test_json_import(json_file_path: str, sample_size: int = 50):
    """JSON 파일 샘플로 import 테스트"""
    print("=" * 60)
    print("JSON Import Test")
    print("=" * 60)
    
    # DATABASE_URL 확인
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found")
        sys.exit(1)
    
    # JSON 파일 확인
    json_path = Path(json_file_path)
    if not json_path.exists():
        print(f"❌ ERROR: JSON file not found: {json_file_path}")
        sys.exit(1)
    
    print(f"\n📂 JSON file: {json_path}")
    print(f"📊 Sample size: {sample_size}")
    
    # JSON 파일 읽기
    print("\n[1/4] Reading JSON file...")
    start_time = time.time()
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            all_items = json.load(f)
        
        if not isinstance(all_items, list):
            print(f"❌ ERROR: JSON is not a list (type: {type(all_items)})")
            sys.exit(1)
        
        # 샘플 추출
        sample_items = all_items[:sample_size] if len(all_items) > sample_size else all_items
        elapsed = time.time() - start_time
        
        print(f"✅ Read {len(all_items)} items, using {len(sample_items)} for test ({elapsed:.2f}s)")
    except Exception as e:
        print(f"❌ ERROR reading JSON: {e}")
        sys.exit(1)
    
    # DB 연결 테스트
    print("\n[2/4] Testing database connection...")
    start_time = time.time()
    try:
        conn = get_db_connection()
        conn.close()
        elapsed = time.time() - start_time
        print(f"✅ Database connection successful ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Database connection failed after {elapsed:.2f}s: {e}")
        sys.exit(1)
    
    # Pipeline run 생성
    print("\n[3/4] Creating pipeline run...")
    try:
        run_id = create_pipeline_run("test", status="running")
        print(f"✅ Pipeline run created: run_id={run_id}")
    except Exception as e:
        print(f"❌ ERROR creating pipeline run: {e}")
        sys.exit(1)
    
    # 데이터 처리 및 적재
    print("\n[4/4] Processing and inserting data...")
    total_start = time.time()
    
    try:
        # 키워드 추출 (파일명에서 또는 기본값)
        keyword = "test_keyword"
        if "spring_dinner_ideas" in json_path.name:
            keyword = "spring dinner ideas"
        elif "easy_spring_meals" in json_path.name:
            keyword = "easy spring meals"
        
        stats = process_apify_results(sample_items, keyword, run_id)
        total_elapsed = time.time() - total_start
        
        # 결과 출력
        print("\n" + "=" * 60)
        print("Test Results")
        print("=" * 60)
        print(f"✅ Processing time: {total_elapsed:.2f}s")
        print(f"✅ Posts processed: {stats.get('posts_collected', 0)}")
        print(f"✅ Comments processed: {stats.get('comments_collected', 0)}")
        print(f"✅ Errors: {len(stats.get('errors', []))}")
        
        if stats.get('errors'):
            print("\n⚠️  Error samples:")
            for error in stats['errors'][:5]:
                print(f"   - {error}")
        
        # 처리량 계산
        total_items = stats.get('posts_collected', 0) + stats.get('comments_collected', 0)
        if total_elapsed > 0:
            throughput = total_items / total_elapsed
            print(f"\n📊 Throughput: {throughput:.2f} items/second")
        
        print("=" * 60)
        
    except Exception as e:
        total_elapsed = time.time() - total_start
        print(f"\n❌ ERROR during processing (after {total_elapsed:.2f}s): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="JSON import test")
    parser.add_argument("--json-file", type=str, 
                       help="Path to JSON file (default: first file in data/ directory)")
    parser.add_argument("--sample-size", type=int, default=50,
                       help="Number of items to test (default: 50)")
    
    args = parser.parse_args()
    
    # JSON 파일 경로 결정
    if args.json_file:
        json_file = args.json_file
    else:
        # data/ 디렉토리에서 첫 번째 JSON 파일 찾기
        data_dir = project_root / "data"
        json_files = list(data_dir.glob("*.json"))
        if not json_files:
            print("❌ ERROR: No JSON files found in data/ directory")
            print("   Use --json-file to specify a file")
            sys.exit(1)
        json_file = str(json_files[0])
        print(f"📂 Using first JSON file found: {json_file}")
    
    test_json_import(json_file, args.sample_size)

if __name__ == "__main__":
    main()
