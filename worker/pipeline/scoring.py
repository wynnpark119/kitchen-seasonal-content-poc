"""
Scoring and trend status calculation
"""
from typing import Dict, Any
from .db import get_db_connection
from .logging import setup_logger

logger = setup_logger("scoring")

def calculate_trend_status(cluster_id: int, run_id: int) -> str:
    """Calculate trend status: Emerging, Competitive, Saturated, Niche"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            # Get recent trend data
            cur.execute("""
                SELECT reddit_post_count, reddit_weighted_score
                FROM cluster_timeseries
                WHERE cluster_id = %s
                AND created_from_run_id = %s
                ORDER BY month DESC
                LIMIT 3
            """, (cluster_id, run_id))
            
            trends = cur.fetchall()
            
            if not trends or len(trends) < 2:
                return "Niche"
            
            # Simple trend calculation
            recent_count = trends[0][0] if trends else 0
            older_count = trends[-1][0] if len(trends) > 1 else 0
            
            if recent_count > older_count * 1.2:
                return "Emerging"
            elif recent_count < older_count * 0.8:
                return "Saturated"
            else:
                return "Competitive"
    
    finally:
        conn.close()

def calculate_scores(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Calculate scores for all briefs"""
    conn = get_db_connection()
    stats = {
        "briefs_scored": 0
    }
    
    try:
        with conn.cursor() as cur:
            # Get all briefs
            cur.execute("""
                SELECT id, cluster_id
                FROM topic_qa_briefs
                WHERE created_from_run_id = %s
            """, (run_id,))
            
            briefs = cur.fetchall()
            logger.info(f"Calculating scores for {len(briefs)} briefs")
            
            for brief_id, cluster_id in briefs:
                if dry_run:
                    if stats["briefs_scored"] < 3:
                        logger.info(f"[DRY RUN] Would calculate score for brief {brief_id}")
                    stats["briefs_scored"] += 1
                    continue
                
                # Calculate trend status
                trend_status = calculate_trend_status(cluster_id, run_id)
                
                # Simple score calculation (could be more sophisticated)
                score = 75.0  # Base score
                if trend_status == "Emerging":
                    score += 15.0
                elif trend_status == "Competitive":
                    score += 5.0
                
                # Update score
                cur.execute("""
                    UPDATE topic_qa_briefs
                    SET score = %s
                    WHERE id = %s
                """, (score, brief_id))
                
                stats["briefs_scored"] += 1
            
            conn.commit()
    
    finally:
        conn.close()
    
    logger.info(f"Scoring completed: {stats['briefs_scored']} briefs scored")
    return stats
