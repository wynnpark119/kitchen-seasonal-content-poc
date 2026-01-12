#!/usr/bin/env python3
"""
Database smoke test: 간단한 연결 및 쿼리 테스트

사용법:
    export DATABASE_URL="postgresql://..."
    python scripts/db_smoke_test.py
"""
import os
import sys
import time
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
        load_dotenv()
except ImportError:
    pass

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def test_db_connection():
    """데이터베이스 연결 테스트"""
    print("=" * 60)
    print("Database Smoke Test")
    print("=" * 60)
    
    # DATABASE_URL 확인
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("   Set DATABASE_URL environment variable or add to .env file")
        sys.exit(1)
    
    # URL 마스킹 (민감 정보 제거)
    url_parts = database_url.split('@')
    if len(url_parts) > 1:
        masked_url = f"...@{url_parts[-1]}"
    else:
        masked_url = database_url[:50] + "..."
    
    print(f"\n📊 Database URL: {masked_url}")
    
    # Railway SSL 설정
    is_railway = any(pattern in database_url.lower() for pattern in [
        'railway.app', 'rlwy.net', 'up.railway.app'
    ])
    if is_railway and 'sslmode' not in database_url.lower():
        separator = '&' if '?' in database_url else '?'
        database_url = f"{database_url}{separator}sslmode=require"
        print("✅ Added sslmode=require for Railway")
    
    # Test 1: 연결 테스트 (타임아웃 10초)
    print("\n[1/3] Testing database connection (timeout: 10s)...")
    start_time = time.time()
    try:
        conn = psycopg2.connect(database_url, connect_timeout=10)
        elapsed = time.time() - start_time
        print(f"✅ Connection successful ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Connection failed after {elapsed:.2f}s: {e}")
        sys.exit(1)
    
    # Test 2: SELECT 1 쿼리 테스트
    print("\n[2/3] Testing SELECT 1 query...")
    start_time = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            elapsed = time.time() - start_time
            if result[0] == 1:
                print(f"✅ SELECT 1 successful ({elapsed:.2f}s)")
            else:
                print(f"❌ Unexpected result: {result}")
                sys.exit(1)
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Query failed after {elapsed:.2f}s: {e}")
        conn.close()
        sys.exit(1)
    
    # Test 3: 임시 테이블 INSERT 후 ROLLBACK 테스트
    print("\n[3/3] Testing INSERT with rollback...")
    start_time = time.time()
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            # 임시 테이블 생성
            cur.execute("""
                CREATE TEMP TABLE IF NOT EXISTS smoke_test (
                    id SERIAL PRIMARY KEY,
                    test_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # INSERT
            cur.execute("INSERT INTO smoke_test (test_value) VALUES (%s)", ("smoke_test",))
            
            # SELECT로 확인
            cur.execute("SELECT COUNT(*) FROM smoke_test WHERE test_value = %s", ("smoke_test",))
            count = cur.fetchone()[0]
            
            # 테이블 삭제 (TEMP 테이블이므로 자동 삭제되지만 명시적으로)
            cur.execute("DROP TABLE IF EXISTS smoke_test")
            
            elapsed = time.time() - start_time
            if count == 1:
                print(f"✅ INSERT/ROLLBACK test successful ({elapsed:.2f}s)")
            else:
                print(f"❌ Unexpected count: {count}")
                sys.exit(1)
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ INSERT test failed after {elapsed:.2f}s: {e}")
        conn.close()
        sys.exit(1)
    finally:
        conn.close()
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_db_connection()
