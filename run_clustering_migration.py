#!/usr/bin/env python3
"""
클러스터링 결과 마이그레이션 실행 스크립트
"""
import os
import sys
import psycopg2
from pathlib import Path
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# .env 파일 로드
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()  # 시스템 환경 변수만 로드
except ImportError:
    # dotenv가 없으면 .env 파일을 직접 읽기
    project_root = Path(__file__).parent
    env_path = project_root / ".env"
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not os.getenv(key):
                            os.environ[key] = value
        except (PermissionError, IOError):
            pass

def main():
    # DATABASE_URL 가져오기
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    
    if not database_url:
        print("❌ 오류: DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # Railway PostgreSQL SSL 설정
    is_railway = any(pattern in database_url.lower() for pattern in [
        'railway.app', 'rlwy.net', 'up.railway.app'
    ])
    
    if is_railway and 'sslmode' not in database_url.lower():
        separator = '&' if '?' in database_url else '?'
        database_url = f"{database_url}{separator}sslmode=require"
    
    # 마이그레이션 파일 경로
    migration_file = Path(__file__).parent / 'migrations' / '006_add_clustering_result_fields.sql'
    
    if not migration_file.exists():
        print(f"❌ 오류: 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        sys.exit(1)
    
    print(f"📄 마이그레이션 파일 읽기: {migration_file.name}")
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    try:
        print(f"🔌 데이터베이스 연결 중...")
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print(f"⚙️  마이그레이션 실행 중: {migration_file.name}")
        cursor.execute(sql_content)
        
        print("✅ 마이그레이션 완료!")
        
        # 컬럼 확인
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'clusters' 
            AND column_name IN ('topic_category', 'sub_cluster_index', 'top_keywords', 'summary', 'cluster_metadata')
            ORDER BY column_name;
        """)
        columns = cursor.fetchall()
        
        if columns:
            print(f"\n추가된 컬럼 ({len(columns)}):")
            for col_name, col_type in columns:
                print(f"  - {col_name} ({col_type})")
        else:
            print("\n⚠️  경고: 컬럼이 확인되지 않았습니다.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
