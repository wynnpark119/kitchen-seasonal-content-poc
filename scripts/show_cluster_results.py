#!/usr/bin/env python3
"""
클러스터링 결과 조회 및 표시 스크립트
"""
import sys
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.logging import setup_logger
import json

logger = setup_logger("show_cluster_results")

def show_cluster_results(run_id: Optional[int] = None):
    """클러스터링 결과 조회 및 표시 (topic_category별로 분리)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if run_id:
                query = """
                    SELECT c.cluster_id, c.params_json, c.size, c.created_at
                    FROM clusters c
                    WHERE c.created_from_run_id = %s
                    AND c.noise_label = FALSE
                    ORDER BY c.cluster_id
                """
                cur.execute(query, (run_id,))
            else:
                # 최신 run_id의 클러스터 조회
                query = """
                    SELECT c.cluster_id, c.params_json, c.size, c.created_at
                    FROM clusters c
                    WHERE c.created_from_run_id = (
                        SELECT MAX(created_from_run_id) 
                        FROM clusters 
                        WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    )
                    AND c.noise_label = FALSE
                    ORDER BY c.cluster_id
                """
                cur.execute(query)
            
            clusters = cur.fetchall()
            
            if not clusters:
                print("❌ 클러스터를 찾을 수 없습니다.")
                return
            
            # topic_category별로 그룹화
            category_clusters = {}
            for cluster_id, params_json, size, created_at in clusters:
                params = params_json if isinstance(params_json, dict) else {}
                # topic_category 또는 category 필드 확인
                category = params.get("topic_category") or params.get("category", "UNKNOWN")
                
                if category not in category_clusters:
                    category_clusters[category] = {
                        "clusters": [],
                        "total_posts": 0,
                        "total_clusters": 0
                    }
                
                category_clusters[category]["clusters"].append({
                    "cluster_id": cluster_id,
                    "params": params,
                    "size": size,
                    "created_at": created_at
                })
                category_clusters[category]["total_posts"] += size
                category_clusters[category]["total_clusters"] += 1
            
            print("=" * 80)
            print(f"클러스터링 결과 (전체 {len(clusters)}개 클러스터)")
            print("=" * 80)
            print("")
            
            # 각 topic_category별로 출력
            for category, cat_data in sorted(category_clusters.items()):
                clusters_list = cat_data["clusters"]
                total_posts = cat_data["total_posts"]
                total_clusters = cat_data["total_clusters"]
                
                print("=" * 80)
                print(f"📌 {category}")
                print("=" * 80)
                print(f"포스트 수: {total_posts}")
                print(f"생성된 sub-cluster 수: {total_clusters}")
                print("")
                
                if total_clusters == 0:
                    print("  ⚠️  데이터 없음")
                    print("")
                    continue
                
                # 각 sub-cluster 출력
                for idx, cluster_info in enumerate(clusters_list, 1):
                    cluster_id = cluster_info["cluster_id"]
                    params = cluster_info["params"]
                    size = cluster_info["size"]
                    created_at = cluster_info["created_at"]
                    
                    top_keywords = params.get("top_keywords", [])
                    summary = params.get("summary", "")
                    representative_post_ids = params.get("representative_post_ids", [])
                    sub_cluster_index = params.get("sub_cluster_index", idx - 1)
                    
                    print(f"  Sub-cluster {sub_cluster_index + 1} (Cluster ID: {cluster_id})")
                    print(f"    포스트 수: {size}")
                    print(f"    생성 시간: {created_at}")
                    
                    if top_keywords:
                        print(f"    대표 키워드: {', '.join(top_keywords[:10])}")
                    
                    if summary:
                        print(f"    요약: {summary[:200]}...")
                    
                    # 대표 포스트 제목 조회
                    if representative_post_ids:
                        cur.execute("""
                            SELECT title, upvotes, num_comments
                            FROM raw_reddit_posts
                            WHERE reddit_post_id = ANY(%s)
                            ORDER BY upvotes DESC, num_comments DESC
                            LIMIT 5
                        """, (representative_post_ids,))
                        
                        posts = cur.fetchall()
                        if posts:
                            print(f"\n    대표 포스트 (상위 5개):")
                            for i, (title, upvotes, num_comments) in enumerate(posts, 1):
                                print(f"      {i}. {title[:60]}... (👍 {upvotes}, 💬 {num_comments})")
                    
                    print("")
                
                print("-" * 80)
                print("")
    
    finally:
        if conn:
            put_db_connection(conn)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Show cluster results")
    parser.add_argument("--run-id", type=int, help="Pipeline run ID (default: latest)")
    args = parser.parse_args()
    
    show_cluster_results(args.run_id)
