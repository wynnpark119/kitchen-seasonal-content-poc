#!/usr/bin/env python3
"""
카테고리 분류 로직 분석 및 subreddit 분포 확인
"""
import sys
from pathlib import Path
from collections import Counter

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.tfidf_clustering import assign_post_to_category, extract_text_from_post
from worker.pipeline.config import CATEGORIES

def analyze_assignment_logic():
    """[1] assign_post_to_category() 함수 분석"""
    print("=" * 80)
    print("[1] assign_post_to_category() 함수 로직 분석")
    print("=" * 80)
    
    print("\n함수 위치: worker/pipeline/tfidf_clustering.py 라인 54-89")
    print("\n현재 로직:")
    print("1. keyword 필드가 있으면 우선 사용 (라인 68-73)")
    print("   - keyword에 카테고리 키워드가 포함되어 있으면 해당 카테고리 반환")
    print("2. 텍스트 기반 매칭 (라인 76-86)")
    print("   - 각 카테고리의 키워드가 텍스트에 나타나는 횟수를 카운트")
    print("   - 가장 높은 점수의 카테고리 반환")
    print("3. 매칭 실패 시 기본값: SPRING_RECIPES (라인 88-89)")
    print("\n⚠️  문제점:")
    print("- subreddit 정보를 전혀 사용하지 않음")
    print("- 키워드 매칭이 너무 느슨함 (예: 'my', 'me' 같은 stopword도 매칭 가능)")
    print("- 매칭 실패 시 무조건 SPRING_RECIPES로 할당")
    print("- AITA, 관계 상담 포스트도 'my', 'me' 같은 단어 때문에 SPRING_RECIPES로 분류될 수 있음")

def analyze_subreddit_distribution():
    """[2] Reddit 데이터의 subreddit 분포 분석"""
    print("\n" + "=" * 80)
    print("[2] Reddit 데이터의 subreddit 분포 분석")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 현재 카테고리 분류로 할당된 포스트들의 subreddit 분포 확인
            print("\n현재 카테고리 분류 기준 subreddit 분포:")
            print("-" * 80)
            
            for category in CATEGORIES:
                print(f"\n{category}:")
                
                # 해당 카테고리로 분류될 포스트들의 subreddit 조회
                cur.execute("""
                    SELECT rp.subreddit, COUNT(*) as count
                    FROM raw_reddit_posts rp
                    WHERE rp.title IS NOT NULL
                    AND LENGTH(COALESCE(rp.title, '')) > 0
                    GROUP BY rp.subreddit
                    ORDER BY count DESC
                    LIMIT 20
                """)
                
                all_subreddits = cur.fetchall()
                
                # 실제로 이 카테고리로 분류되는지 확인
                category_subreddits = {}
                for subreddit, count in all_subreddits:
                    # 샘플 포스트로 카테고리 할당 확인
                    cur.execute("""
                        SELECT title, body, keyword
                        FROM raw_reddit_posts
                        WHERE subreddit = %s
                        AND title IS NOT NULL
                        LIMIT 5
                    """, (subreddit,))
                    
                    sample_posts = cur.fetchall()
                    category_counts = Counter()
                    
                    for title, body, keyword in sample_posts:
                        post_text = extract_text_from_post(title, body)
                        assigned = assign_post_to_category(post_text, keyword)
                        category_counts[assigned] += 1
                    
                    # 이 subreddit이 이 카테고리로 분류되는 비율
                    if category_counts[category] > 0:
                        category_subreddits[subreddit] = {
                            'total': count,
                            'assigned_to_category': category_counts[category],
                            'sample_size': len(sample_posts)
                        }
                
                # 상위 10개 출력
                sorted_subs = sorted(category_subreddits.items(), 
                                    key=lambda x: x[1]['total'], reverse=True)[:10]
                
                if sorted_subs:
                    for subreddit, info in sorted_subs:
                        print(f"  - r/{subreddit}: {info['total']}개 포스트 "
                              f"(샘플 중 {info['assigned_to_category']}/{info['sample_size']}개가 {category}로 분류)")
                else:
                    print("  (분류된 subreddit 없음)")
            
            # SPRING_RECIPES에 포함된 모든 subreddit 목록
            print("\n" + "=" * 80)
            print("SPRING_RECIPES에 포함된 subreddit 전체 목록:")
            print("=" * 80)
            
            cur.execute("""
                SELECT DISTINCT rp.subreddit, COUNT(*) as count
                FROM raw_reddit_posts rp
                WHERE rp.title IS NOT NULL
                AND LENGTH(COALESCE(rp.title, '')) > 0
                GROUP BY rp.subreddit
                ORDER BY count DESC
            """)
            
            all_subreddits = cur.fetchall()
            
            spring_recipes_subs = []
            for subreddit, count in all_subreddits:
                # 샘플로 확인
                cur.execute("""
                    SELECT title, body, keyword
                    FROM raw_reddit_posts
                    WHERE subreddit = %s
                    AND title IS NOT NULL
                    LIMIT 10
                """, (subreddit,))
                
                sample_posts = cur.fetchall()
                spring_count = 0
                
                for title, body, keyword in sample_posts:
                    post_text = extract_text_from_post(title, body)
                    assigned = assign_post_to_category(post_text, keyword)
                    if assigned == "SPRING_RECIPES":
                        spring_count += 1
                
                if spring_count > len(sample_posts) * 0.5:  # 50% 이상이 SPRING_RECIPES로 분류되면
                    spring_recipes_subs.append((subreddit, count, spring_count, len(sample_posts)))
            
            print(f"\n총 {len(spring_recipes_subs)}개 subreddit이 SPRING_RECIPES로 분류됨:")
            for subreddit, total, spring_count, sample_size in sorted(spring_recipes_subs, 
                                                                      key=lambda x: x[1], 
                                                                      reverse=True):
                print(f"  - r/{subreddit}: {total}개 포스트 "
                      f"(샘플 {spring_count}/{sample_size}개가 SPRING_RECIPES)")
    
    finally:
        if conn:
            put_db_connection(conn)

if __name__ == "__main__":
    analyze_assignment_logic()
    analyze_subreddit_distribution()
