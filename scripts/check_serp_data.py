#!/usr/bin/env python3
"""
SERP 데이터 확인 및 샘플링 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.logging import setup_logger

logger = setup_logger("check_serp_data")

def check_serp_data():
    """SERP 데이터 확인 및 샘플링"""
    import time
    
    conn = None
    max_retries = 3
    
    for retry in range(max_retries):
        try:
            conn = get_db_connection()
            break
        except Exception as e:
            if retry < max_retries - 1:
                wait_time = 2 ** retry
                logger.warning(f"DB 연결 실패 (시도 {retry + 1}/{max_retries}), {wait_time}초 후 재시도: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"DB 연결 실패 (최대 재시도 횟수 초과): {e}")
                raise
    
    try:
        cur = conn.cursor()
        
        print("=" * 80)
        print("SERP 데이터 확인 및 샘플링 테스트")
        print("=" * 80)
        print()
        
        # 1. 전체 통계
        print("1. 전체 통계")
        print("-" * 80)
        cur.execute("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT topic_category) as topic_count,
                COUNT(DISTINCT query) as query_count,
                COUNT(DISTINCT url) as unique_urls,
                MIN(fetched_at) as first_fetched,
                MAX(fetched_at) as last_fetched
            FROM serp_results
        """)
        total = cur.fetchone()
        print(f"  총 row 수: {total[0]:,}")
        print(f"  topic_category 수: {total[1]}")
        print(f"  고유 query 수: {total[2]}")
        print(f"  고유 URL 수: {total[3]:,}")
        print(f"  첫 수집 시간: {total[4]}")
        print(f"  마지막 수집 시간: {total[5]}")
        print()
        
        # 2. topic_category별 통계
        print("2. topic_category별 통계")
        print("-" * 80)
        cur.execute("""
            SELECT 
                topic_category,
                COUNT(*) as row_count,
                COUNT(DISTINCT query) as query_count,
                COUNT(DISTINCT url) as unique_urls,
                AVG(position)::numeric(5,2) as avg_position
            FROM serp_results
            GROUP BY topic_category
            ORDER BY topic_category
        """)
        
        print(f"{'topic_category':<30} {'row_count':<12} {'query_count':<12} {'unique_urls':<12} {'avg_position':<12}")
        print("-" * 80)
        for row in cur.fetchall():
            print(f"{row[0]:<30} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<12}")
        print()
        
        # 3. 각 topic_category별 샘플 (5개씩)
        print("3. 각 topic_category별 샘플 데이터 (5개씩)")
        print("-" * 80)
        
        for topic_category in ["SPRING_RECIPES", "REFRIGERATOR_ORGANIZATION", 
                               "VEGETABLE_PREP_HANDLING", "SPRING_KITCHEN_STYLING"]:
            print()
            print(f"[{topic_category}]")
            print("-" * 80)
            
            cur.execute("""
                SELECT query, title, url, snippet, position, source, fetched_at
                FROM serp_results
                WHERE topic_category = %s
                ORDER BY fetched_at DESC, position ASC
                LIMIT 5
            """, (topic_category,))
            
            rows = cur.fetchall()
            if not rows:
                print("  (데이터 없음)")
                continue
            
            for i, (query, title, url, snippet, position, source, fetched_at) in enumerate(rows, 1):
                print(f"  {i}. Query: {query}")
                print(f"     Position: {position} | Source: {source}")
                print(f"     Title: {title[:80] if title else 'N/A'}...")
                print(f"     URL: {url[:80]}...")
                if snippet:
                    snippet_preview = snippet[:150] + "..." if len(snippet) > 150 else snippet
                    print(f"     Snippet: {snippet_preview}")
                print(f"     Fetched: {fetched_at}")
                print()
        
        # 4. 쿼리별 결과 수 통계
        print("4. 쿼리별 결과 수 통계 (상위 10개)")
        print("-" * 80)
        cur.execute("""
            SELECT 
                topic_category,
                query,
                COUNT(*) as result_count
            FROM serp_results
            GROUP BY topic_category, query
            ORDER BY result_count DESC
            LIMIT 10
        """)
        
        print(f"{'topic_category':<30} {'query':<50} {'results':<10}")
        print("-" * 80)
        for row in cur.fetchall():
            query_preview = row[1][:47] + "..." if len(row[1]) > 50 else row[1]
            print(f"{row[0]:<30} {query_preview:<50} {row[2]:<10}")
        print()
        
        # 5. 도메인별 통계 (상위 10개)
        print("5. 도메인별 통계 (상위 10개)")
        print("-" * 80)
        cur.execute("""
            SELECT 
                source,
                COUNT(*) as count,
                COUNT(DISTINCT topic_category) as topic_count
            FROM serp_results
            WHERE source IS NOT NULL
            GROUP BY source
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print(f"{'source':<40} {'count':<10} {'topic_count':<12}")
        print("-" * 80)
        for row in cur.fetchall():
            print(f"{row[0]:<40} {row[1]:<10} {row[2]:<12}")
        print()
        
        # 6. 데이터 품질 확인
        print("6. 데이터 품질 확인")
        print("-" * 80)
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE title IS NULL OR title = '') as null_title,
                COUNT(*) FILTER (WHERE snippet IS NULL OR snippet = '') as null_snippet,
                COUNT(*) FILTER (WHERE url IS NULL OR url = '') as null_url,
                COUNT(*) FILTER (WHERE source IS NULL OR source = '') as null_source
            FROM serp_results
        """)
        quality = cur.fetchone()
        print(f"  Title 없는 row: {quality[0]}")
        print(f"  Snippet 없는 row: {quality[1]}")
        print(f"  URL 없는 row: {quality[2]}")
        print(f"  Source 없는 row: {quality[3]}")
        print()
        
        print("=" * 80)
        print("데이터 확인 완료!")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"데이터 확인 중 오류: {e}", exc_info=True)
        raise
    finally:
        if conn:
            put_db_connection(conn)

if __name__ == "__main__":
    check_serp_data()
