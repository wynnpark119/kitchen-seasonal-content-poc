#!/usr/bin/env python3
"""
빠른 검증 스크립트 - 최신 run_id의 결과만 확인
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.config import CATEGORIES

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
        latest_run_id = result[0] if result and result[0] else None
        
        if not latest_run_id:
            print("⚠️  클러스터 데이터 없음")
            sys.exit(1)
        
        print(f"최신 Run ID: {latest_run_id}\n")
        
        # 클러스터 수
        cur.execute("""
            SELECT COUNT(*) FROM clusters
            WHERE created_from_run_id = %s
            AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
        """, (latest_run_id,))
        cluster_count = cur.fetchone()[0]
        
        # 할당 수
        cur.execute("""
            SELECT COUNT(*) FROM cluster_assignments ca
            JOIN clusters c ON ca.cluster_id = c.cluster_id
            WHERE c.created_from_run_id = %s
            AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
        """, (latest_run_id,))
        assignment_count = cur.fetchone()[0]
        
        print(f"생성된 클러스터 수: {cluster_count}")
        print(f"생성된 할당 수: {assignment_count}\n")
        
        # 카테고리별 통계
        print("topic_category별 통계:")
        for category in CATEGORIES:
            cur.execute("""
                SELECT COUNT(*) as clusters,
                       COUNT(DISTINCT ca.doc_id) as posts
                FROM clusters c
                LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
                WHERE c.created_from_run_id = %s
                AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                AND (
                    c.params_json->>'topic_category' = %s
                    OR c.params_json->>'category' = %s
                )
            """, (latest_run_id, category, category))
            
            result = cur.fetchone()
            clusters = result[0] if result else 0
            posts = result[1] if result else 0
            
            print(f"  {category}: {clusters} clusters, {posts} posts")
        
        if cluster_count > 0 and assignment_count > 0:
            print("\n✅ 클러스터링 결과가 DB에 저장되었습니다!")
        else:
            print("\n⚠️  클러스터 데이터가 없거나 불완전합니다.")

finally:
    if conn:
        put_db_connection(conn)
