#!/usr/bin/env python3
"""
데이터베이스에 저장된 키워드 확인
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection
from worker.pipeline.config import REDDIT_KEYWORDS, CATEGORIES

def check_collected_keywords():
    """데이터베이스에 저장된 키워드 확인"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 저장된 키워드 목록 조회
            cur.execute("""
                SELECT DISTINCT keyword, COUNT(*) as post_count
                FROM raw_reddit_posts
                WHERE keyword IS NOT NULL
                GROUP BY keyword
                ORDER BY keyword
            """)
            collected = cur.fetchall()
            
            print("=" * 60)
            print("데이터베이스에 저장된 키워드")
            print("=" * 60)
            
            if collected:
                for keyword, count in collected:
                    print(f"  {keyword}: {count}개 포스트")
                print(f"\n총 {len(collected)}개 키워드 수집 완료")
            else:
                print("  저장된 키워드가 없습니다.")
            
            # 카테고리별 수집 현황
            print("\n" + "=" * 60)
            print("카테고리별 수집 현황")
            print("=" * 60)
            
            all_keywords = []
            for category in CATEGORIES:
                keywords_in_category = REDDIT_KEYWORDS.get(category, [])
                all_keywords.extend(keywords_in_category)
            
            collected_keywords = {kw: count for kw, count in collected} if collected else {}
            
            for category in CATEGORIES:
                keywords_in_category = REDDIT_KEYWORDS.get(category, [])
                collected_in_category = [kw for kw in keywords_in_category if kw in collected_keywords]
                print(f"\n[{category}]")
                print(f"  수집 완료: {len(collected_in_category)}/{len(keywords_in_category)}")
                if collected_in_category:
                    for kw in collected_in_category:
                        print(f"    ✓ {kw} ({collected_keywords[kw]}개)")
                missing = [kw for kw in keywords_in_category if kw not in collected_keywords]
                if missing:
                    print(f"  미수집: {len(missing)}개")
                    if len(missing) <= 10:
                        for kw in missing:
                            print(f"    ✗ {kw}")
                    else:
                        print(f"    (첫 10개만 표시)")
                        for kw in missing[:10]:
                            print(f"    ✗ {kw}")
            
            print("\n" + "=" * 60)
            print(f"전체 수집 현황: {len(collected_keywords)}/{len(all_keywords)}")
            print("=" * 60)
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_collected_keywords()
