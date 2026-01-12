#!/usr/bin/env python3
"""
클러스터링 결과 JSON 파일을 DB에 적재하는 스크립트
"""
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List

# .env 파일 로드
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not os.getenv(key):
                            os.environ[key] = value
        except (PermissionError, IOError):
            pass

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection, create_pipeline_run, update_pipeline_run
from worker.pipeline.logging import setup_logger
from psycopg2.extras import Json as PsycopgJson, execute_batch

logger = setup_logger("load_clusters_json")

def load_clusters_from_json(json_path: str, run_id: int):
    """클러스터링 결과 JSON을 DB에 적재"""
    print("=" * 80)
    print("클러스터링 결과 DB 적재")
    print("=" * 80)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    clusters = data.get('clusters', [])
    metadata = data.get('metadata', {})
    
    print(f"\nJSON 파일 정보:")
    print(f"  - 전체 포스트 수: {metadata.get('total_posts', 0)}")
    print(f"  - 전체 클러스터 수: {len(clusters)}")
    
    conn = None
    stats = {
        "clusters_inserted": 0,
        "assignments_inserted": 0,
        "errors": []
    }
    
    try:
        conn = get_db_connection()
        
        # 기존 클러스터 삭제 (선택사항)
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM cluster_assignments 
                WHERE created_from_run_id = %s
            """, (run_id,))
            
            cur.execute("""
                DELETE FROM clusters 
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """, (run_id,))
            
            conn.commit()
            print("\n✅ 기존 클러스터 데이터 삭제 완료")
        
        # 각 클러스터를 DB에 저장
        for cluster in clusters:
            try:
                with conn.cursor() as cur:
                    # 클러스터 저장
                    params = {
                        "method": "tfidf_kmeans",
                        "topic_category": cluster['topic_category'],
                        "sub_cluster_index": cluster['sub_cluster_index'],
                        "top_keywords": cluster.get('top_keywords', []),
                        "representative_post_ids": cluster.get('representative_post_ids', []),
                        "summary": cluster.get('summary', '')
                    }
                    
                    cur.execute("""
                        INSERT INTO clusters (
                            algorithm, params_json, noise_label, size, created_from_run_id
                        ) VALUES (%s, %s, %s, %s, %s)
                        RETURNING cluster_id
                    """, (
                        "TF-IDF_KMEANS",
                        PsycopgJson(params),
                        False,
                        cluster['size'],
                        run_id
                    ))
                    
                    cluster_id = cur.fetchone()[0]
                    stats["clusters_inserted"] += 1
                    
                    # 클러스터 할당 저장
                    post_ids = cluster.get('post_ids', [])
                    assignments_data = []
                    
                    for post_id in post_ids:
                        is_rep = post_id in cluster.get('representative_post_ids', [])
                        assignments_data.append((
                            cluster_id,
                            "reddit_post",
                            post_id,
                            0.0,  # distance
                            is_rep,
                            run_id
                        ))
                    
                    if assignments_data:
                        execute_batch(cur, """
                            INSERT INTO cluster_assignments (
                                cluster_id, doc_type, doc_id, distance_to_centroid,
                                is_representative, created_from_run_id
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (doc_type, doc_id, created_from_run_id) DO UPDATE SET
                                cluster_id = EXCLUDED.cluster_id,
                                distance_to_centroid = EXCLUDED.distance_to_centroid,
                                is_representative = EXCLUDED.is_representative,
                                updated_at = CURRENT_TIMESTAMP
                        """, assignments_data, page_size=100)
                        
                        stats["assignments_inserted"] += len(assignments_data)
                    
                    conn.commit()
                    
                    print(f"  ✅ 클러스터 {cluster_id} ({cluster['topic_category']}): "
                          f"{cluster['size']}개 포스트, {len(assignments_data)}개 할당")
            
            except Exception as e:
                logger.error(f"클러스터 저장 실패 ({cluster.get('cluster_id')}): {e}", exc_info=True)
                stats["errors"].append(f"cluster_{cluster.get('cluster_id')}: {str(e)}")
                if conn:
                    conn.rollback()
                continue
        
        print("\n" + "=" * 80)
        print("적재 완료")
        print("=" * 80)
        print(f"  - 클러스터 삽입: {stats['clusters_inserted']}개")
        print(f"  - 할당 삽입: {stats['assignments_inserted']}개")
        print(f"  - 에러: {len(stats['errors'])}개")
        
        return stats
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"데이터 적재 실패: {e}", exc_info=True)
        raise
    finally:
        if conn:
            put_db_connection(conn)

def validate_clusters_in_db(run_id: int):
    """DB에 저장된 클러스터 검증"""
    print("\n" + "=" * 80)
    print("DB 저장 결과 검증")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # topic_category별 통계
            cur.execute("""
                SELECT 
                    params_json->>'topic_category' as topic_category,
                    COUNT(*) as cluster_count,
                    SUM(size) as total_posts
                FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm = 'TF-IDF_KMEANS'
                GROUP BY params_json->>'topic_category'
                ORDER BY params_json->>'topic_category'
            """, (run_id,))
            
            print("\ntopic_category별 클러스터 통계:")
            print(f"{'Topic':<40} | {'Clusters':<10} | {'Posts':<10}")
            print("-" * 65)
            
            for category, cluster_count, total_posts in cur.fetchall():
                print(f"{category or 'UNKNOWN':<40} | {cluster_count:<10} | {total_posts or 0:<10}")
            
            # 전체 통계
            cur.execute("""
                SELECT COUNT(*) FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm = 'TF-IDF_KMEANS'
            """, (run_id,))
            total_clusters = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) FROM cluster_assignments ca
                JOIN clusters c ON ca.cluster_id = c.cluster_id
                WHERE c.created_from_run_id = %s
                AND c.algorithm = 'TF-IDF_KMEANS'
            """, (run_id,))
            total_assignments = cur.fetchone()[0]
            
            print(f"\n전체 통계:")
            print(f"  - 클러스터 수: {total_clusters}개")
            print(f"  - 할당 수: {total_assignments}개")
    
    finally:
        if conn:
            put_db_connection(conn)

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="클러스터링 결과 JSON을 DB에 적재")
    parser.add_argument("json_file", help="클러스터링 결과 JSON 파일 경로")
    
    args = parser.parse_args()
    
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {json_path}")
        sys.exit(1)
    
    # Pipeline run 생성
    run_id = create_pipeline_run("cluster_load_from_json", status="running")
    print(f"Run ID: {run_id}\n")
    
    try:
        # 클러스터 적재
        stats = load_clusters_from_json(str(json_path), run_id)
        
        # 검증
        validate_clusters_in_db(run_id)
        
        # Pipeline run 완료
        update_pipeline_run(run_id, "completed", metadata=stats)
        
        print("\n✅ 완료!")
        return 0
    
    except Exception as e:
        logger.error(f"실행 실패: {e}", exc_info=True)
        update_pipeline_run(run_id, "failed", error_message=str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())
