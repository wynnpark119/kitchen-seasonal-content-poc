"""
HDBSCAN clustering and representative sample selection
"""
import numpy as np
from typing import List, Dict, Any, Tuple
import hdbscan
from .config import HDBSCAN_MIN_CLUSTER_SIZE, HDBSCAN_MIN_SAMPLES, HDBSCAN_METRIC, REPRESENTATIVE_SAMPLES_K
from .db import get_db_connection, upsert_cluster_assignment
from .logging import setup_logger

logger = setup_logger("clustering")

def load_embeddings(run_id: int) -> Tuple[List[str], np.ndarray]:
    """Load embeddings from database"""
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
                doc_ids.append(doc_id)
                embeddings.append(embedding_json)
    
    finally:
        conn.close()
    
    return doc_ids, np.array(embeddings)

def run_clustering(embeddings: np.ndarray) -> Tuple[hdbscan.HDBSCAN, Dict[int, List[int]]]:
    """Run HDBSCAN clustering"""
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

def calculate_centroid(embeddings: np.ndarray, indices: List[int]) -> np.ndarray:
    """Calculate cluster centroid"""
    cluster_embeddings = embeddings[indices]
    return np.mean(cluster_embeddings, axis=0)

def find_representative_samples(embeddings: np.ndarray, cluster_indices: List[int], 
                               centroid: np.ndarray, k: int = REPRESENTATIVE_SAMPLES_K) -> List[int]:
    """Find k representative samples closest to centroid"""
    cluster_embeddings = embeddings[cluster_indices]
    
    # Calculate distances to centroid
    distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
    
    # Get top k closest
    top_k_indices = np.argsort(distances)[:k]
    return [cluster_indices[i] for i in top_k_indices]

def save_clusters(cluster_groups: Dict[int, List[int]], doc_ids: List[str], 
                 embeddings: np.ndarray, clusterer: hdbscan.HDBSCAN, run_id: int) -> Dict[str, Any]:
    """Save clusters and assignments to database"""
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
                    continue
                
                # Create cluster record
                cur.execute("""
                    INSERT INTO clusters (
                        algorithm, params_json, noise_label, size, created_from_run_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING cluster_id
                """, (
                    "HDBSCAN",
                    '{"min_cluster_size": ' + str(HDBSCAN_MIN_CLUSTER_SIZE) + 
                    ', "min_samples": ' + str(HDBSCAN_MIN_SAMPLES) + 
                    ', "metric": "' + HDBSCAN_METRIC + '"}',
                    False,
                    len(indices),
                    run_id
                ))
                cluster_id = cur.fetchone()[0]
                stats["clusters_created"] += 1
                
                # Calculate centroid
                centroid = calculate_centroid(embeddings, indices)
                
                # Find representative samples
                rep_indices = find_representative_samples(embeddings, indices, centroid)
                
                # Save assignments
                for idx in indices:
                    doc_id = doc_ids[idx]
                    distance = np.linalg.norm(embeddings[idx] - centroid)
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
    """Run full clustering pipeline"""
    logger.info("Starting clustering pipeline")
    
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
    
    # Save clusters
    stats = save_clusters(cluster_groups, doc_ids, embeddings, clusterer, run_id)
    logger.info(f"Clustering pipeline completed: {stats['clusters_created']} clusters, {stats['noise_points']} noise points")
    
    return stats
