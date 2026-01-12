#!/usr/bin/env python3
"""
데이터베이스 테이블 확인 스크립트
"""
import os
import sys
import psycopg2

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    try:
        print("데이터베이스 연결 중...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # 테이블 목록 조회
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print(f"\n✅ 생성된 테이블 ({len(tables)}개):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 각 테이블의 데이터 개수 확인
        print("\n📊 테이블별 데이터 개수:")
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count}개")
            except Exception as e:
                print(f"  - {table_name}: 확인 실패 ({e})")
        
        # 컬럼 확인 (raw_serp_aio의 aio_status, topic_qa_briefs의 insights_json)
        print("\n🔍 마이그레이션 컬럼 확인:")
        
        # aio_status 확인
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'raw_serp_aio' 
              AND column_name = 'aio_status';
        """)
        if cursor.fetchone():
            print("  ✅ raw_serp_aio.aio_status 컬럼 존재")
        else:
            print("  ❌ raw_serp_aio.aio_status 컬럼 없음")
        
        # insights_json 확인
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'topic_qa_briefs' 
              AND column_name = 'insights_json';
        """)
        if cursor.fetchone():
            print("  ✅ topic_qa_briefs.insights_json 컬럼 존재")
        else:
            print("  ❌ topic_qa_briefs.insights_json 컬럼 없음")
        
        cursor.close()
        conn.close()
        
        print("\n✅ 확인 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
