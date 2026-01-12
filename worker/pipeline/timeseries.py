"""
Timeseries aggregation: monthly trends per cluster

카테고리별 시즌성 해석 로직 포함:
- SEASONAL_CATEGORIES: 봄 시즌 baseline 계산 및 spring_adjusted_lift
- EVERGREEN_CATEGORIES: 절대 증가 기준
"""
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from .db import get_db_connection
from .config import SEASONAL_CATEGORIES, EVERGREEN_CATEGORIES
from .logging import setup_logger

logger = setup_logger("timeseries")

# 봄 시즌 정의
SPRING_MONTHS = [3, 4, 5]  # March, April, May

def calculate_weighted_score(upvotes: int, num_comments: int) -> float:
    """
    Reddit weighted score 계산
    
    Formula: log1p(upvotes) + 0.5 * log1p(num_comments)
    """
    return float(np.log1p(upvotes) + 0.5 * np.log1p(num_comments))

def get_cluster_category(cluster_id: int, run_id: int) -> Optional[str]:
    """
    클러스터의 카테고리 확인 (키워드 기반 추정)
    
    Returns:
        Category name or None
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 클러스터의 키워드 확인
            cur.execute("""
                SELECT DISTINCT keyword
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
                LIMIT 10
            """, (cluster_id, run_id))
            
            keywords = [row[0].lower() for row in cur.fetchall() if row[0]]
            
            # 키워드 기반 카테고리 추정
            for keyword in keywords:
                if any(term in keyword for term in ['spring', 'recipe', 'meal', 'dinner', 'cook']):
                    if any(term in keyword for term in ['recipe', 'meal', 'dinner', 'cook']):
                        return "SPRING_RECIPES"
                    elif any(term in keyword for term in ['decor', 'styling', 'style', 'refresh']):
                        return "SPRING_KITCHEN_STYLING"
                elif any(term in keyword for term in ['refrigerator', 'fridge', 'organization']):
                    return "REFRIGERATOR_ORGANIZATION"
                elif any(term in keyword for term in ['vegetable', 'prep', 'wash', 'store']):
                    return "VEGETABLE_PREP_HANDLING"
            
            return None
    finally:
        conn.close()

def calculate_spring_baseline(cluster_id: int, run_id: int) -> Tuple[float, int]:
    """
    봄 시즌 historical baseline 계산
    
    월별 집계된 weighted_score의 평균 사용
    
    Returns:
        (baseline_score, baseline_count) - 봄 시즌 평균 점수와 월 수
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 봄 시즌 월별 집계 데이터 조회 (기존 시계열 데이터 활용)
            cur.execute("""
                SELECT 
                    month,
                    reddit_weighted_score,
                    reddit_post_count
                FROM cluster_timeseries
                WHERE cluster_id = %s
                AND created_from_run_id = %s
                AND EXTRACT(MONTH FROM month) IN (3, 4, 5)
                ORDER BY month DESC
            """, (cluster_id, run_id))
            
            spring_timeseries = cur.fetchall()
            
            if not spring_timeseries:
                # 봄 시계열 데이터가 없으면 전체 평균 사용
                cur.execute("""
                    SELECT 
                        AVG(reddit_weighted_score) as avg_score,
                        COUNT(*) as month_count
                    FROM cluster_timeseries
                    WHERE cluster_id = %s
                    AND created_from_run_id = %s
                """, (cluster_id, run_id))
                
                result = cur.fetchone()
                if result and result[0]:
                    return (float(result[0]), int(result[1] or 0))
                return (0.0, 0)
            
            # 봄 시즌 월별 weighted_score 평균
            spring_scores = [float(score or 0) for _, score, _ in spring_timeseries]
            baseline_score = np.mean(spring_scores) if spring_scores else 0.0
            baseline_count = len(spring_timeseries)  # 봄 시즌 월 수
            
            return (baseline_score, baseline_count)
    
    finally:
        conn.close()

def interpret_seasonal_trend(current_score: float, baseline_score: float) -> str:
    """
    시즌성 카테고리 트렌드 해석
    
    Returns:
        "SEASONAL_EXPECTED", "SEASONAL_OUTPERFORM", "SEASONAL_UNDERPERFORM"
    """
    if baseline_score == 0:
        return "SEASONAL_EXPECTED"
    
    lift_ratio = (current_score - baseline_score) / baseline_score
    
    if lift_ratio > 0.2:  # 20% 이상 초과
        return "SEASONAL_OUTPERFORM"
    elif lift_ratio < -0.2:  # 20% 이상 미달
        return "SEASONAL_UNDERPERFORM"
    else:
        return "SEASONAL_EXPECTED"

def interpret_evergreen_trend(timeseries: List[Tuple[datetime, int, float]]) -> str:
    """
    비시즌성 카테고리 트렌드 해석
    
    Returns:
        "EMERGING", "STEADY", "DECLINING"
    """
    if len(timeseries) < 2:
        return "STEADY"
    
    # 최근 3개월 가중 점수
    recent_scores = [score for _, _, score in timeseries[:3]]
    recent_avg = np.mean(recent_scores) if recent_scores else 0.0
    
    # 이전 기간 평균
    older_scores = [score for _, _, score in timeseries[3:6]] if len(timeseries) > 3 else []
    older_avg = np.mean(older_scores) if older_scores else recent_avg
    
    if older_avg == 0:
        return "STEADY"
    
    growth_ratio = (recent_avg - older_avg) / older_avg
    
    if growth_ratio > 0.3:  # 30% 이상 증가
        return "EMERGING"
    elif growth_ratio < -0.2:  # 20% 이상 감소
        return "DECLINING"
    else:
        return "STEADY"

def generate_timeseries(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    Generate monthly timeseries data for clusters
    
    카테고리별 시즌성 해석 로직 적용
    """
    conn = get_db_connection()
    stats = {
        "clusters_processed": 0,
        "months_aggregated": 0,
        "seasonal_clusters": 0,
        "evergreen_clusters": 0
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
                # 카테고리 확인
                category = get_cluster_category(cluster_id, run_id)
                is_seasonal = category in SEASONAL_CATEGORIES if category else False
                
                if is_seasonal:
                    stats["seasonal_clusters"] += 1
                else:
                    stats["evergreen_clusters"] += 1
                
                # Get posts in cluster with dates
                cur.execute("""
                    SELECT 
                        DATE_TRUNC('month', TO_TIMESTAMP(rp.created_utc)) as month,
                        COUNT(*) as post_count,
                        SUM(rp.upvotes) as total_upvotes,
                        SUM(rp.num_comments) as total_comments,
                        SUM(LOG(1 + rp.upvotes) + 0.5 * LOG(1 + rp.num_comments)) as weighted_score_sum
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
                        logger.info(f"[DRY RUN] Cluster {cluster_id} ({category or 'unknown'}): {len(monthly_data)} months")
                    stats["clusters_processed"] += 1
                    continue
                
                # Insert timeseries data (baseline 계산은 scoring 단계에서 수행)
                for month, post_count, total_upvotes, total_comments, weighted_score_sum in monthly_data:
                    # weighted_score_sum이 이미 계산되어 있으면 사용, 아니면 계산
                    if weighted_score_sum:
                        weighted_score = float(weighted_score_sum)
                    else:
                        # Fallback: 개별 계산
                        weighted_score = calculate_weighted_score(int(total_upvotes or 0), int(total_comments or 0))
                    
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
                        weighted_score,
                        run_id
                    ))
                    stats["months_aggregated"] += 1
                
                stats["clusters_processed"] += 1
                conn.commit()
    
    finally:
        conn.close()
    
    logger.info(f"Timeseries generation completed:")
    logger.info(f"  Clusters processed: {stats['clusters_processed']}")
    logger.info(f"  Months aggregated: {stats['months_aggregated']}")
    logger.info(f"  Seasonal clusters: {stats['seasonal_clusters']}")
    logger.info(f"  Evergreen clusters: {stats['evergreen_clusters']}")
    
    return stats
