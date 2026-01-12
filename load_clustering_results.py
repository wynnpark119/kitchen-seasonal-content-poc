"""
클러스터링 결과 JSON을 데이터베이스에 적재하는 스크립트
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# .env 파일 로드
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()  # 시스템 환경 변수만 로드
except ImportError:
    # dotenv가 없으면 .env 파일을 직접 읽기
    project_root = Path(__file__).parent
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

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import (
    get_db_connection,
    put_db_connection,
    create_pipeline_run,
    update_pipeline_run,
)
from psycopg2.extras import execute_batch, Json as PsycopgJson


def load_clustering_results(json_path: str, run_type: str = "clustering_load") -> Dict[str, Any]:
    """
    클러스터링 결과 JSON을 데이터베이스에 적재
    
    Args:
        json_path: 클러스터링 결과 JSON 파일 경로
        run_type: 파이프라인 실행 타입
    
    Returns:
        적재 결과 통계
    """
    # JSON 파일 로드
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
    
    print(f"클러스터링 결과 JSON 로드 중: {json_path}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    clusters = data.get('clusters', [])
    
    print(f"총 클러스터 수: {len(clusters)}")
    print(f"총 포스트 수: {metadata.get('total_posts', 0)}")
    
    # 파이프라인 run 생성
    run_id = create_pipeline_run(run_type=run_type, status="running")
    print(f"파이프라인 run 생성: run_id={run_id}")
    
    conn = None
    stats = {
        "clusters_inserted": 0,
        "assignments_inserted": 0,
        "errors": 0
    }
    
    try:
        conn = get_db_connection()
        
        # 클러스터 할당 데이터 준비
        assignment_inserts = []
        
        # 클러스터 삽입 (개별 삽입하여 cluster_id 받기)
        cluster_id_map = {}  # (topic_category, sub_cluster_index) -> cluster_id
        if clusters:
            print(f"클러스터 {len(clusters)}개 삽입 중...")
            with conn.cursor() as cur:
                for idx, cluster_data in enumerate(clusters):
                    try:
                        topic_category = cluster_data.get('topic_category', '')
                        sub_cluster_index = cluster_data.get('sub_cluster_index', 0)
                        size = cluster_data.get('size', 0)
                        top_keywords = cluster_data.get('top_keywords', [])
                        summary = cluster_data.get('summary', '')
                        cluster_id_str = cluster_data.get('cluster_id', '')
                        representative_post_ids = cluster_data.get('representative_post_ids', [])
                        
                        # 클러스터 메타데이터 준비
                        cluster_metadata = {
                            "original_cluster_id": cluster_id_str,
                            "representative_post_ids": representative_post_ids,
                        }
                        
                        # 클러스터 삽입 (RETURNING으로 cluster_id 받기)
                        cur.execute("""
                            INSERT INTO clusters (
                                algorithm, params_json, noise_label, size,
                                topic_category, sub_cluster_index, top_keywords,
                                summary, cluster_metadata, created_from_run_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING cluster_id
                        """, (
                            'HDBSCAN',  # algorithm
                            PsycopgJson({}),  # params_json
                            False,  # noise_label
                            size,  # size
                            topic_category,  # topic_category
                            sub_cluster_index,  # sub_cluster_index
                            PsycopgJson(top_keywords) if top_keywords else None,  # top_keywords
                            summary[:10000] if summary else None,  # summary
                            PsycopgJson(cluster_metadata),  # cluster_metadata
                            run_id,  # created_from_run_id
                        ))
                        
                        db_cluster_id = cur.fetchone()[0]
                        cluster_id_map[(topic_category, sub_cluster_index)] = db_cluster_id
                        stats["clusters_inserted"] += 1
                        
                    except Exception as e:
                        print(f"클러스터 삽입 중 오류 (cluster_id={cluster_data.get('cluster_id', 'unknown')}): {e}")
                        stats["errors"] += 1
                        continue
                
                conn.commit()
                print(f"✅ 클러스터 {stats['clusters_inserted']}개 삽입 완료")
        
        # 클러스터 할당 데이터 준비 및 삽입
        cluster_idx = 0
        for cluster_data in clusters:
            try:
                topic_category = cluster_data.get('topic_category', '')
                sub_cluster_index = cluster_data.get('sub_cluster_index', 0)
                post_ids = cluster_data.get('post_ids', [])
                representative_post_ids = set(cluster_data.get('representative_post_ids', []))
                
                # DB 클러스터 ID 가져오기
                db_cluster_id = cluster_id_map.get((topic_category, sub_cluster_index))
                if not db_cluster_id:
                    print(f"경고: 클러스터 ID를 찾을 수 없음 (topic_category={topic_category}, sub_cluster_index={sub_cluster_index})")
                    stats["errors"] += 1
                    continue
                
                # 포스트 할당 데이터 준비
                for post_id in post_ids:
                    is_representative = post_id in representative_post_ids
                    assignment_inserts.append((
                        db_cluster_id,  # cluster_id
                        'reddit_post',  # doc_type
                        post_id,  # doc_id
                        None,  # distance_to_centroid (없음)
                        is_representative,  # is_representative
                        run_id,  # created_from_run_id
                    ))
                
                cluster_idx += 1
                
            except Exception as e:
                print(f"클러스터 할당 데이터 준비 중 오류 (cluster_id={cluster_data.get('cluster_id', 'unknown')}): {e}")
                stats["errors"] += 1
                continue
        
        # 클러스터 할당 배치 삽입
        if assignment_inserts:
            print(f"클러스터 할당 {len(assignment_inserts)}개 삽입 중...")
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO cluster_assignments (
                        cluster_id, doc_type, doc_id, distance_to_centroid,
                        is_representative, created_from_run_id
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_type, doc_id, created_from_run_id) DO UPDATE SET
                        cluster_id = EXCLUDED.cluster_id,
                        is_representative = EXCLUDED.is_representative,
                        updated_at = CURRENT_TIMESTAMP
                """, assignment_inserts, page_size=100)
                
                conn.commit()
                stats["assignments_inserted"] = len(assignment_inserts)
                print(f"✅ 클러스터 할당 {stats['assignments_inserted']}개 삽입 완료")
        
        # 파이프라인 run 완료 처리
        update_pipeline_run(
            run_id=run_id,
            status="completed",
            metadata={
                "clusters_inserted": stats["clusters_inserted"],
                "assignments_inserted": stats["assignments_inserted"],
                "errors": stats["errors"],
                "total_clusters": len(clusters),
                "total_posts": metadata.get('total_posts', 0),
            }
        )
        print(f"✅ 파이프라인 run 완료: run_id={run_id}")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 오류 발생: {e}")
        stats["errors"] += 1
        
        # 파이프라인 run 실패 처리
        try:
            update_pipeline_run(
                run_id=run_id,
                status="failed",
                error_message=str(e)
            )
        except:
            pass
        
        raise
    
    finally:
        if conn:
            put_db_connection(conn)
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="클러스터링 결과 JSON을 DB에 적재")
    parser.add_argument(
        "json_path",
        type=str,
        help="클러스터링 결과 JSON 파일 경로"
    )
    parser.add_argument(
        "--run-type",
        type=str,
        default="clustering_load",
        help="파이프라인 실행 타입 (기본값: clustering_load)"
    )
    
    args = parser.parse_args()
    
    try:
        stats = load_clustering_results(args.json_path, args.run_type)
        print("\n" + "="*50)
        print("적재 완료!")
        print("="*50)
        print(f"클러스터 삽입: {stats['clusters_inserted']}개")
        print(f"할당 삽입: {stats['assignments_inserted']}개")
        print(f"오류: {stats['errors']}개")
        print("="*50)
    except Exception as e:
        print(f"\n❌ 적재 실패: {e}")
        sys.exit(1)
