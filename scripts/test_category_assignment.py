#!/usr/bin/env python3
"""
수정된 카테고리 분류 로직 테스트 및 검증
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.tfidf_clustering import assign_post_to_category, extract_text_from_post
from worker.pipeline.config import CATEGORIES

def test_category_assignment():
    """카테고리 분류만 재실행 및 검증"""
    print("=" * 80)
    print("카테고리 분류 테스트 및 검증")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 각 카테고리별로 포스트 분류
            category_posts = {category: [] for category in CATEGORIES}
            unassigned_count = 0
            
            cur.execute("""
                SELECT reddit_post_id, title, body, keyword, subreddit
                FROM raw_reddit_posts
                WHERE title IS NOT NULL
                AND LENGTH(COALESCE(title, '')) > 0
                ORDER BY upvotes DESC, num_comments DESC
                LIMIT 1000
            """)
            
            all_posts = cur.fetchall()
            
            for post_id, title, body, keyword, subreddit in all_posts:
                post_text = extract_text_from_post(title, body)
                category = assign_post_to_category(post_text, keyword, subreddit)
                
                if category is None:
                    unassigned_count += 1
                    continue
                
                category_posts[category].append({
                    "post_id": post_id,
                    "title": title,
                    "subreddit": subreddit
                })
            
            print(f"\n전체 처리된 포스트: {len(all_posts)}")
            print(f"할당되지 않은 포스트: {unassigned_count}")
            print(f"할당된 포스트: {sum(len(posts) for posts in category_posts.values())}\n")
            
            # 각 topic_category별 결과
            print("=" * 80)
            print("topic_category별 결과")
            print("=" * 80)
            
            for category in CATEGORIES:
                posts = category_posts[category]
                print(f"\n{category}: {len(posts)}개 포스트")
                
                if len(posts) > 0:
                    print(f"\n  상위 10개 샘플:")
                    for i, post in enumerate(posts[:10], 1):
                        print(f"    {i}. [{post['subreddit']}] {post['title'][:70]}...")
                    
                    # subreddit 분포
                    subreddit_counts = {}
                    for post in posts:
                        sub = post['subreddit']
                        subreddit_counts[sub] = subreddit_counts.get(sub, 0) + 1
                    
                    print(f"\n  Subreddit 분포 (상위 10개):")
                    for sub, count in sorted(subreddit_counts.items(), 
                                           key=lambda x: x[1], reverse=True)[:10]:
                        print(f"    - r/{sub}: {count}개")
                else:
                    print("  (포스트 없음)")
            
            # 검증: 주제 일관성 확인
            print("\n" + "=" * 80)
            print("주제 일관성 검증")
            print("=" * 80)
            
            all_good = True
            for category in CATEGORIES:
                posts = category_posts[category]
                if len(posts) == 0:
                    continue
                
                # 요리/주방 관련이 아닌 subreddit이 있는지 확인
                problematic_subs = []
                for post in posts[:20]:  # 샘플 20개 확인
                    sub = post['subreddit'].lower()
                    # 제외 목록에 있는지 확인
                    excluded = ['aita', 'amitheasshole', 'relationship', 'tifu', 
                               'unpopularopinion', 'changemyview', 'offmychest']
                    if any(exc in sub for exc in excluded):
                        problematic_subs.append(post['subreddit'])
                
                if problematic_subs:
                    print(f"\n⚠️  {category}: 문제가 있는 subreddit 발견")
                    print(f"   {set(problematic_subs)}")
                    all_good = False
                else:
                    print(f"\n✅ {category}: 주제 일관성 확인됨")
            
            print("\n" + "=" * 80)
            print("최종 판정")
            print("=" * 80)
            
            if all_good and sum(len(posts) for posts in category_posts.values()) > 0:
                print("✅ PASS: 카테고리 분류가 올바르게 작동합니다.")
                print("   다음 단계(클러스터링 재실행)로 진행 가능합니다.")
                return True
            else:
                print("❌ FAIL: 카테고리 분류에 문제가 있습니다.")
                print("   추가 수정이 필요합니다.")
                return False
    
    finally:
        if conn:
            put_db_connection(conn)

if __name__ == "__main__":
    success = test_category_assignment()
    sys.exit(0 if success else 1)
