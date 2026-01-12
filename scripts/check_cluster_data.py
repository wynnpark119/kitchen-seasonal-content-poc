#!/usr/bin/env python3
"""
DB에 실제로 클러스터링 데이터가 있는지 확인
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection

conn = None
try:
    conn = get_db_connection()
    with conn.cursor() as cur:
        # 모든 클러스터 확인
        cur.execute("""
            SELECT cluster_id, algorithm, params_json, size, created_from_run_id, created_at
            FROM clusters
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        clusters = cur.fetchall()
        print(f"전체 클러스터 수: {len(clusters)}")
        
        if clusters:
            print("\n최근 클러스터 샘플:")
            for cluster_id, algorithm, params_json, size, run_id, created_at in clusters[:5]:
                params = params_json if isinstance(params_json, dict) else {}
                topic_cat = params.get("topic_category") or params.get("category", "N/A")
                print(f"  Cluster {cluster_id}: {algorithm}, size={size}, run_id={run_id}, category={topic_cat}")
        else:
            print("\n⚠️  클러스터가 없습니다.")
        
        # 모든 run_id 확인
        cur.execute("""
            SELECT run_id, run_type, status, started_at
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT 10
        """)
        
        runs = cur.fetchall()
        print(f"\n최근 pipeline runs: {len(runs)}")
        for run_id, run_type, status, started_at in runs:
            print(f"  Run {run_id}: {run_type}, status={status}, started={started_at}")
        
        # raw_reddit_posts 확인
        cur.execute("SELECT COUNT(*) FROM raw_reddit_posts")
        post_count = cur.fetchone()[0]
        print(f"\nraw_reddit_posts 수: {post_count}")

finally:
    if conn:
        put_db_connection(conn)
