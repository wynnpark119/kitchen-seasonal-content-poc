#!/usr/bin/env python3
"""
데이터베이스 쿼리 실행 스크립트
사용법: python3 migrations/run_query.py "SELECT * FROM table_name LIMIT 10;"
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        print("사용법: export DATABASE_URL='...' && python3 migrations/run_query.py 'SQL 쿼리'")
        sys.exit(1)
    
    # SQL 쿼리 가져오기
    if len(sys.argv) < 2:
        print("사용법: python3 migrations/run_query.py 'SQL 쿼리'")
        print("\n예시:")
        print("  python3 migrations/run_query.py \"SELECT * FROM pipeline_runs;\"")
        print("  python3 migrations/run_query.py \"\\dt\"  # 테이블 목록")
        sys.exit(1)
    
    query = sys.argv[1]
    
    try:
        print(f"데이터베이스 연결 중...")
        conn = psycopg2.connect(database_url)
        
        # \dt 같은 psql 명령어 처리
        if query == "\\dt":
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print(f"\n테이블 목록 ({len(tables)}개):")
            for table in tables:
                print(f"  - {table[0]}")
            cursor.close()
        else:
            # 일반 SQL 쿼리 실행
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query)
            
            # 결과 출력
            if cursor.description:
                # SELECT 쿼리인 경우
                rows = cursor.fetchall()
                if rows:
                    # 컬럼명 출력
                    columns = [desc[0] for desc in cursor.description]
                    print("\n" + " | ".join(columns))
                    print("-" * 80)
                    
                    # 데이터 출력
                    for row in rows:
                        values = [str(row[col]) if row[col] is not None else "NULL" for col in columns]
                        print(" | ".join(values))
                    
                    print(f"\n총 {len(rows)}개 행")
                else:
                    print("결과 없음")
            else:
                # INSERT, UPDATE, DELETE 등
                print(f"✅ 쿼리 실행 완료")
                print(f"영향받은 행: {cursor.rowcount}개")
            
            cursor.close()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
