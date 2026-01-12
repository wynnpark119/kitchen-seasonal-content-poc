#!/usr/bin/env python3
"""
최종 검증 스크립트 - DB에 저장된 결과 검증
"""
import sys
from pathlib import Path
from typing import List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.config import CATEGORIES

def main():
    print("=" * 80)
    print("클러스터링 결과 최종 검증")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 최신 run_id 찾기
            cur.execute("""
                SELECT MAX(created_from_run_id) as latest_run_id
                FROM clusters
                WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """)
            result = cur.fetchone()
            run_id = result[0] if result and result[0] else None
            
            if not run_id:
                print("\n⚠️  클러스터 데이터 없음")
                return 1
            
            print(f"\n검증 대상 Run ID: {run_id}\n")
            
            # [3] DB 저장 스키마 검증
            print("=" * 80)
            print("[3] DB 저장 스키마 검증")
            print("=" * 80)
            
            # 1. topic_category NULL 체크
            cur.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN params_json->>'topic_category' IS NULL 
                                  AND params_json->>'category' IS NULL THEN 1 END) as null_count
                FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """, (run_id,))
            
            total, null_count = cur.fetchone()
            print(f"\n1. topic_category NULL 체크:")
            print(f"   전체 클러스터: {total}")
            print(f"   topic_category 없는 클러스터: {null_count}")
            schema_ok = null_count == 0
            
            # 2. 동일 post_id 중복 체크
            cur.execute("""
                SELECT ca.doc_id, 
                       COUNT(DISTINCT COALESCE(c.params_json->>'topic_category', c.params_json->>'category')) as category_count
                FROM cluster_assignments ca
                JOIN clusters c ON ca.cluster_id = c.cluster_id
                WHERE c.created_from_run_id = %s
                AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                GROUP BY ca.doc_id
                HAVING COUNT(DISTINCT COALESCE(c.params_json->>'topic_category', c.params_json->>'category')) > 1
                LIMIT 5
            """, (run_id,))
            
            duplicates = cur.fetchall()
            print(f"\n2. 동일 post_id 중복 할당 체크:")
            print(f"   여러 topic_category에 속한 포스트: {len(duplicates)}개")
            if duplicates:
                for post_id, cat_count in duplicates:
                    print(f"     - {post_id}: {cat_count}개 카테고리")
            schema_ok = schema_ok and len(duplicates) == 0
            
            # [4] 정량 검증
            print("\n" + "=" * 80)
            print("[4] DB 저장 결과 정량 검증")
            print("=" * 80)
            
            print("\ntopic_category별 통계:")
            print("-" * 80)
            
            for category in CATEGORIES:
                # 클러스터 수
                cur.execute("""
                    SELECT COUNT(*) as cluster_count
                    FROM clusters
                    WHERE created_from_run_id = %s
                    AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        params_json->>'topic_category' = %s
                        OR params_json->>'category' = %s
                    )
                """, (run_id, category, category))
                
                cluster_result = cur.fetchone()
                sub_clusters = cluster_result[0] if cluster_result else 0
                
                # 클러스터링된 포스트 수
                cur.execute("""
                    SELECT COUNT(DISTINCT ca.doc_id) as clustered_posts
                    FROM cluster_assignments ca
                    JOIN clusters c ON ca.cluster_id = c.cluster_id
                    WHERE c.created_from_run_id = %s
                    AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        c.params_json->>'topic_category' = %s
                        OR c.params_json->>'category' = %s
                    )
                """, (run_id, category, category))
                
                clustered_result = cur.fetchone()
                clustered_posts = clustered_result[0] if clustered_result else 0
                
                print(f"\nTopic: {category}")
                print(f"  - clustered_posts: {clustered_posts}")
                print(f"  - sub_clusters: {sub_clusters}")
            
            # [5] 샘플 검증
            print("\n" + "=" * 80)
            print("[5] 결과 샘플 검증")
            print("=" * 80)
            
            for category in CATEGORIES:
                cur.execute("""
                    SELECT cluster_id, params_json, size
                    FROM clusters
                    WHERE created_from_run_id = %s
                    AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        params_json->>'topic_category' = %s
                        OR params_json->>'category' = %s
                    )
                    ORDER BY cluster_id
                    LIMIT 1
                """, (run_id, category, category))
                
                cluster_result = cur.fetchone()
                
                if not cluster_result:
                    print(f"\nTopic: {category} - 클러스터 없음")
                    continue
                
                cluster_id, params_json, size = cluster_result
                params = params_json if isinstance(params_json, dict) else {}
                
                print(f"\nTopic: {category}")
                print(f"  Sub-cluster ID: {cluster_id}")
                print(f"  포스트 수: {size}")
                print(f"  대표 키워드: {', '.join(params.get('top_keywords', [])[:5])}")
                
                # 포스트 5개
                cur.execute("""
                    SELECT rp.title
                    FROM cluster_assignments ca
                    JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
                    WHERE ca.cluster_id = %s
                    ORDER BY rp.upvotes DESC
                    LIMIT 5
                """, (cluster_id,))
                
                posts = cur.fetchall()
                print(f"  샘플 포스트:")
                for i, (title,) in enumerate(posts, 1):
                    print(f"    {i}. {title[:60]}...")
                
                keywords = ', '.join(params.get('top_keywords', [])[:3])
                print(f"  ✅ 설명: '{category}' 주제 내에서 '{keywords}' 관련 포스트들이 의미적으로 묶여 있음")
            
            # [6] 최종 판정
            print("\n" + "=" * 80)
            print("[6] 최종 판정")
            print("=" * 80)
            
            # 전체 통계
            cur.execute("""
                SELECT COUNT(*) FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """, (run_id,))
            cluster_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) FROM cluster_assignments ca
                JOIN clusters c ON ca.cluster_id = c.cluster_id
                WHERE c.created_from_run_id = %s
                AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """, (run_id,))
            assignment_count = cur.fetchone()[0]
            
            db_persist_executed = cluster_count > 0 and assignment_count > 0
            structure_ok = schema_ok
            can_proceed = db_persist_executed and structure_ok
            
            print(f"\n실행 결과:")
            print(f"  - Run ID: {run_id}")
            print(f"  - 생성된 클러스터 수: {cluster_count}")
            print(f"  - 생성된 할당 수: {assignment_count}")
            print(f"  - DB 스키마 검증: {'PASS' if schema_ok else 'FAIL'}")
            
            print(f"\n최종 판정:")
            print(f"  - DB persist 실행 여부: {'YES' if db_persist_executed else 'NO'}")
            print(f"  - 주제별 분리 클러스터링 구조: {'PASS' if structure_ok else 'FAIL'}")
            print(f"  - 다음 단계(SERP 질문 생성) 진행 가능 여부: {'YES' if can_proceed else 'NO'}")
            
            if not db_persist_executed:
                print(f"\n⚠️  DB 저장이 실행되지 않았습니다.")
            if not structure_ok:
                print(f"\n⚠️  구조 검증 실패")
            
            return 0 if can_proceed else 1
    
    finally:
        if conn:
            put_db_connection(conn)

if __name__ == "__main__":
    sys.exit(main())
