"""
HDBSCAN clustering and representative sample selection

Medoid 기준 대표 샘플 선정 (centroid 대신)
"""
import numpy as np
import json
from typing import List, Dict, Any, Tuple
import hdbscan
from psycopg2.extras import Json
from .config import HDBSCAN_MIN_CLUSTER_SIZE, HDBSCAN_MIN_SAMPLES, HDBSCAN_METRIC, REPRESENTATIVE_SAMPLES_K
from .db import get_db_connection, upsert_cluster_assignment
from .logging import setup_logger

logger = setup_logger("clustering")

def load_embeddings(run_id: int) -> Tuple[List[str], np.ndarray]:
    """
    Load embeddings from database (JSONB format)
    
    Returns:
        (doc_ids, embeddings_array)
    """
    conn = get_db_connection()
    doc_ids = []
    embeddings = []
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.doc_id, e.embedding_json
                FROM embeddings e
                WHERE e.doc_type = 'reddit_post'
                AND e.created_from_run_id = %s
                ORDER BY e.doc_id
            """, (run_id,))
            
            for doc_id, embedding_json in cur.fetchall():
                # embedding_json은 JSONB이므로 리스트로 변환
                if isinstance(embedding_json, list):
                    embedding_list = embedding_json
                elif isinstance(embedding_json, str):
                    embedding_list = json.loads(embedding_json)
                else:
                    embedding_list = list(embedding_json) if embedding_json else []
                
                if len(embedding_list) > 0:
                    doc_ids.append(doc_id)
                    embeddings.append(embedding_list)
    
    finally:
        conn.close()
    
    if len(embeddings) == 0:
        return [], np.array([])
    
    return doc_ids, np.array(embeddings, dtype=np.float32)

def run_clustering(embeddings: np.ndarray) -> Tuple[hdbscan.HDBSCAN, Dict[int, List[int]]]:
    """
    Run HDBSCAN clustering
    
    Returns:
        (clusterer, cluster_groups) where cluster_groups maps label -> list of indices
    """
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
        min_samples=HDBSCAN_MIN_SAMPLES,
        metric=HDBSCAN_METRIC
    )
    
    cluster_labels = clusterer.fit_predict(embeddings)
    
    # Group documents by cluster
    cluster_groups = {}
    for idx, label in enumerate(cluster_labels):
        if label not in cluster_groups:
            cluster_groups[label] = []
        cluster_groups[label].append(idx)
    
    return clusterer, cluster_groups

def find_medoid(embeddings: np.ndarray, indices: List[int]) -> Tuple[int, np.ndarray]:
    """
    Find medoid (클러스터 내 평균 거리가 최소인 문서)
    
    Args:
        embeddings: 전체 임베딩 배열
        indices: 클러스터 내 문서 인덱스 리스트
    
    Returns:
        (medoid_index, medoid_embedding)
    """
    cluster_embeddings = embeddings[indices]
    
    # 각 문서와 다른 모든 문서 간의 거리 계산
    distances = np.zeros(len(cluster_embeddings))
    for i, emb_i in enumerate(cluster_embeddings):
        # 다른 모든 문서와의 거리 합
        dist_sum = np.sum(np.linalg.norm(cluster_embeddings - emb_i, axis=1))
        distances[i] = dist_sum
    
    # 평균 거리가 최소인 문서 (medoid)
    medoid_local_idx = np.argmin(distances)
    medoid_global_idx = indices[medoid_local_idx]
    medoid_embedding = cluster_embeddings[medoid_local_idx]
    
    return medoid_global_idx, medoid_embedding

def find_representative_samples(embeddings: np.ndarray, cluster_indices: List[int], 
                               medoid_embedding: np.ndarray, k: int = REPRESENTATIVE_SAMPLES_K) -> List[int]:
    """
    Find k representative samples closest to medoid
    
    Args:
        embeddings: 전체 임베딩 배열
        cluster_indices: 클러스터 내 문서 인덱스 리스트
        medoid_embedding: Medoid 임베딩 벡터
        k: 대표 샘플 개수
    
    Returns:
        List of representative sample indices
    """
    cluster_embeddings = embeddings[cluster_indices]
    
    # Calculate distances to medoid
    distances = np.linalg.norm(cluster_embeddings - medoid_embedding, axis=1)
    
    # Get top k closest
    top_k_local_indices = np.argsort(distances)[:k]
    return [cluster_indices[i] for i in top_k_local_indices]

def save_clusters(cluster_groups: Dict[int, List[int]], doc_ids: List[str], 
                 embeddings: np.ndarray, clusterer: hdbscan.HDBSCAN, run_id: int) -> Dict[str, Any]:
    """
    Save clusters and assignments to database
    
    Medoid 기준 대표 샘플 선정
    """
    conn = get_db_connection()
    stats = {
        "clusters_created": 0,
        "noise_points": 0,
        "assignments_created": 0,
        "representative_samples": 0
    }
    
    try:
        with conn.cursor() as cur:
            for cluster_label, indices in cluster_groups.items():
                if cluster_label == -1:  # Noise
                    stats["noise_points"] = len(indices)
                    logger.info(f"Noise cluster: {len(indices)} points")
                    continue
                
                # Create cluster record
                params = {
                    "min_cluster_size": HDBSCAN_MIN_CLUSTER_SIZE,
                    "min_samples": HDBSCAN_MIN_SAMPLES,
                    "metric": HDBSCAN_METRIC
                }
                cur.execute("""
                    INSERT INTO clusters (
                        algorithm, params_json, noise_label, size, created_from_run_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING cluster_id
                """, (
                    "HDBSCAN",
                    Json(params),
                    False,
                    len(indices),
                    run_id
                ))
                cluster_id = cur.fetchone()[0]
                stats["clusters_created"] += 1
                
                # Find medoid (centroid 대신)
                medoid_idx, medoid_embedding = find_medoid(embeddings, indices)
                
                # Find representative samples (medoid 기준 top-k)
                rep_indices = find_representative_samples(embeddings, indices, medoid_embedding)
                
                logger.info(f"Cluster {cluster_id}: size={len(indices)}, medoid_idx={medoid_idx}, representatives={len(rep_indices)}")
                
                # Save assignments
                for idx in indices:
                    doc_id = doc_ids[idx]
                    # Medoid 기준 거리
                    distance = np.linalg.norm(embeddings[idx] - medoid_embedding)
                    is_rep = idx in rep_indices
                    
                    upsert_cluster_assignment(
                        cluster_id=cluster_id,
                        doc_type="reddit_post",
                        doc_id=doc_id,
                        distance=distance,
                        is_representative=is_rep,
                        run_id=run_id
                    )
                    stats["assignments_created"] += 1
                    
                    if is_rep:
                        stats["representative_samples"] += 1
                
                conn.commit()
    
    finally:
        conn.close()
    
    return stats

def run_clustering_pipeline(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    Run full clustering pipeline
    
    Medoid 기준 대표 샘플 선정 사용
    """
    logger.info("Starting clustering pipeline (using medoid for representative samples)")
    
    if dry_run:
        logger.info("[DRY RUN] Would load embeddings and run HDBSCAN clustering")
        return {"clusters_created": 0, "noise_points": 0}
    
    # Load embeddings
    doc_ids, embeddings = load_embeddings(run_id)
    logger.info(f"Loaded {len(doc_ids)} embeddings")
    
    if len(embeddings) == 0:
        logger.warning("No embeddings found, skipping clustering")
        return {"clusters_created": 0, "noise_points": 0}
    
    # Run clustering
    clusterer, cluster_groups = run_clustering(embeddings)
    logger.info(f"Clustering completed: {len(cluster_groups)} groups (including noise)")
    
    # Calculate noise ratio
    noise_count = len(cluster_groups.get(-1, []))
    total_count = len(doc_ids)
    noise_ratio = noise_count / total_count if total_count > 0 else 0.0
    logger.info(f"Noise points: {noise_count} ({noise_ratio:.2%})")
    
    # Save clusters
    stats = save_clusters(cluster_groups, doc_ids, embeddings, clusterer, run_id)
    logger.info(f"Clustering pipeline completed:")
    logger.info(f"  Clusters created: {stats['clusters_created']}")
    logger.info(f"  Noise points: {stats['noise_points']} ({noise_ratio:.2%})")
    logger.info(f"  Assignments created: {stats['assignments_created']}")
    logger.info(f"  Representative samples: {stats['representative_samples']}")
    
    return stats
