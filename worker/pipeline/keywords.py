"""
Keyword extraction using TF-IDF
"""
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from .config import TOP_KEYWORDS_COUNT
from .db import get_db_connection
from .logging import setup_logger

logger = setup_logger("keywords")

def extract_keywords_for_cluster(cluster_id: int, run_id: int) -> List[str]:
    """Extract top keywords for a cluster using TF-IDF"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            # Get all posts in cluster
            cur.execute("""
                SELECT rp.title, rp.body
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
            """, (cluster_id, run_id))
            
            posts = cur.fetchall()
            
            if not posts:
                return []
            
            # Combine titles and bodies
            documents = [f"{title} {body}" for title, body in posts]
            
            # TF-IDF
            vectorizer = TfidfVectorizer(max_features=TOP_KEYWORDS_COUNT * 2, stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(documents)
            
            # Get feature names and scores
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            
            # Sort by score
            top_indices = scores.argsort()[-TOP_KEYWORDS_COUNT:][::-1]
            keywords = [feature_names[i] for i in top_indices]
            
            return keywords.tolist()
    
    finally:
        conn.close()

def extract_keywords_for_all_clusters(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Extract keywords for all clusters"""
    conn = get_db_connection()
    stats = {
        "clusters_processed": 0,
        "keywords_extracted": 0
    }
    
    try:
        with conn.cursor() as cur:
            # Get all clusters
            cur.execute("""
                SELECT cluster_id
                FROM clusters
                WHERE created_from_run_id = %s
                AND noise_label = FALSE
            """, (run_id,))
            
            clusters = cur.fetchall()
            logger.info(f"Extracting keywords for {len(clusters)} clusters")
            
            for (cluster_id,) in clusters:
                keywords = extract_keywords_for_cluster(cluster_id, run_id)
                
                if dry_run:
                    if stats["clusters_processed"] < 3:
                        logger.info(f"[DRY RUN] Cluster {cluster_id} keywords: {keywords[:5]}")
                else:
                    # Store keywords (could create cluster_keywords table or store in metadata)
                    stats["keywords_extracted"] += len(keywords)
                
                stats["clusters_processed"] += 1
    
    finally:
        conn.close()
    
    logger.info(f"Keyword extraction completed: {stats['keywords_extracted']} keywords extracted")
    return stats
