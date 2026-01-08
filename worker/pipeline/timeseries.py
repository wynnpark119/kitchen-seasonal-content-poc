"""
Timeseries aggregation: monthly trends per cluster
"""
from typing import Dict, Any
from datetime import datetime, timedelta
from .db import get_db_connection
from .logging import setup_logger

logger = setup_logger("timeseries")

def generate_timeseries(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Generate monthly timeseries data for clusters"""
    conn = get_db_connection()
    stats = {
        "clusters_processed": 0,
        "months_aggregated": 0
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
            logger.info(f"Generating timeseries for {len(clusters)} clusters")
            
            for (cluster_id,) in clusters:
                # Get posts in cluster with dates
                cur.execute("""
                    SELECT 
                        DATE_TRUNC('month', TO_TIMESTAMP(rp.created_utc)) as month,
                        COUNT(*) as post_count,
                        AVG(rp.upvotes) as avg_upvotes,
                        SUM(rp.upvotes) as total_upvotes
                    FROM raw_reddit_posts rp
                    JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                    WHERE ca.cluster_id = %s
                    AND ca.created_from_run_id = %s
                    GROUP BY month
                    ORDER BY month DESC
                """, (cluster_id, run_id))
                
                monthly_data = cur.fetchall()
                
                if dry_run:
                    if stats["clusters_processed"] < 2:
                        logger.info(f"[DRY RUN] Cluster {cluster_id} timeseries: {len(monthly_data)} months")
                    stats["clusters_processed"] += 1
                    continue
                
                # Insert timeseries data
                for month, post_count, avg_upvotes, total_upvotes in monthly_data:
                    cur.execute("""
                        INSERT INTO cluster_timeseries (
                            cluster_id, month, reddit_post_count,
                            reddit_weighted_score, created_from_run_id
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (cluster_id, month, created_from_run_id) DO UPDATE SET
                            reddit_post_count = EXCLUDED.reddit_post_count,
                            reddit_weighted_score = EXCLUDED.reddit_weighted_score,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        cluster_id,
                        month,
                        int(post_count),
                        float(total_upvotes or 0),
                        run_id
                    ))
                    stats["months_aggregated"] += 1
                
                stats["clusters_processed"] += 1
                conn.commit()
    
    finally:
        conn.close()
    
    logger.info(f"Timeseries generation completed: {stats['months_aggregated']} month records created")
    return stats
