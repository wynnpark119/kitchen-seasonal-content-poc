"""
Scoring and cluster prioritization for brief generation

카테고리별 시즌성 해석 로직 포함:
- SEASONAL_CATEGORIES: 봄 시즌 baseline 기반 해석
- EVERGREEN_CATEGORIES: 절대 증가 기준 해석
"""
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from .db import get_db_connection
from .config import SEASONAL_CATEGORIES, EVERGREEN_CATEGORIES
from .timeseries import (
    get_cluster_category, 
    calculate_spring_baseline, 
    interpret_seasonal_trend, 
    interpret_evergreen_trend,
    SPRING_MONTHS
)
from .logging import setup_logger

logger = setup_logger("scoring")

def calculate_cluster_priority_score(cluster_id: int, run_id: int) -> Tuple[float, Dict[str, Any]]:
    """
    클러스터 우선순위 점수 계산
    
    Returns:
        (score, breakdown) - 점수와 상세 내역
    """
    conn = get_db_connection()
    breakdown = {
        "reddit_score": 0.0,
        "gsc_score": 0.0,
        "aio_penalty": 0.0,
        "total": 0.0
    }
    
    try:
        with conn.cursor() as cur:
            # 1. Reddit weighted score (최근 3개월 가중)
            # 가중치: 최근 3개월 = [1.0, 0.7, 0.5]
            cur.execute("""
                SELECT month, reddit_weighted_score
                FROM cluster_timeseries
                WHERE cluster_id = %s
                AND created_from_run_id = %s
                ORDER BY month DESC
                LIMIT 3
            """, (cluster_id, run_id))
            
            timeseries = cur.fetchall()
            weights = [1.0, 0.7, 0.5]
            reddit_score = 0.0
            
            for i, (month, weighted_score) in enumerate(timeseries):
                if i < len(weights):
                    reddit_score += float(weighted_score or 0) * weights[i]
            
            breakdown["reddit_score"] = reddit_score
            
            # 2. GSC impressions (있으면)
            cur.execute("""
                SELECT DISTINCT keyword
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
                LIMIT 5
            """, (cluster_id, run_id))
            
            cluster_keywords = [row[0] for row in cur.fetchall()]
            gsc_score = 0.0
            
            if cluster_keywords:
                cur.execute("""
                    SELECT SUM(impressions) as total_impressions
                    FROM raw_gsc_queries
                    WHERE query ILIKE ANY(ARRAY[%s])
                """, ([f"%{kw}%" for kw in cluster_keywords],))
                
                result = cur.fetchone()
                if result and result[0]:
                    total_impressions = float(result[0])
                    gsc_score = min(100.0, total_impressions / 100.0)
                    breakdown["gsc_score"] = gsc_score
            
            # 3. AIO AVAILABLE 페널티 (소폭)
            aio_penalty = 0.0
            if cluster_keywords:
                cur.execute("""
                    SELECT COUNT(*) as aio_count
                    FROM raw_serp_aio
                    WHERE query ILIKE ANY(ARRAY[%s])
                    AND aio_status = 'AVAILABLE'
                """, ([f"%{kw}%" for kw in cluster_keywords[:3]],))
                
                result = cur.fetchone()
                if result and result[0] > 0:
                    aio_penalty = 5.0
                    breakdown["aio_penalty"] = aio_penalty
            
            # 총 점수
            total_score = reddit_score + gsc_score - aio_penalty
            breakdown["total"] = total_score
            
            return total_score, breakdown
    
    finally:
        conn.close()

def calculate_trend_status_with_seasonality(cluster_id: int, run_id: int) -> Tuple[str, Dict[str, Any]]:
    """
    카테고리별 시즌성 해석 로직 적용 트렌드 상태 계산
    
    Returns:
        (trend_status, trend_metadata)
        - trend_status: "SEASONAL_EXPECTED", "SEASONAL_OUTPERFORM", "SEASONAL_UNDERPERFORM",
                        "EMERGING", "STEADY", "DECLINING", "Niche"
        - trend_metadata: 시즌성 해석 상세 정보
    """
    conn = get_db_connection()
    trend_metadata = {
        "category": None,
        "is_seasonal": False,
        "interpretation": None,
        "spring_baseline": None,
        "spring_adjusted_lift": None,
        "recent_score": None,
        "older_score": None
    }
    
    try:
        with conn.cursor() as cur:
            # 카테고리 확인
            category = get_cluster_category(cluster_id, run_id)
            trend_metadata["category"] = category
            is_seasonal = category in SEASONAL_CATEGORIES if category else False
            trend_metadata["is_seasonal"] = is_seasonal
            
            # Get recent trend data (최근 3개월)
            cur.execute("""
                SELECT month, reddit_post_count, reddit_weighted_score
                FROM cluster_timeseries
                WHERE cluster_id = %s
                AND created_from_run_id = %s
                ORDER BY month DESC
                LIMIT 6
            """, (cluster_id, run_id))
            
            trends = cur.fetchall()
            
            if not trends or len(trends) < 2:
                return "Niche", trend_metadata
            
            # 최근 3개월 데이터
            recent_timeseries = trends[:3]
            recent_scores = [float(t[2] or 0) for t in recent_timeseries]
            recent_avg = np.mean(recent_scores) if recent_scores else 0.0
            trend_metadata["recent_score"] = recent_avg
            
            # 이전 기간 (4-6개월 전)
            older_timeseries = trends[3:6] if len(trends) > 3 else []
            older_scores = [float(t[2] or 0) for t in older_timeseries]
            older_avg = np.mean(older_scores) if older_scores else recent_avg
            trend_metadata["older_score"] = older_avg
            
            # 시즌성 카테고리 해석
            if is_seasonal:
                # 봄 시즌 baseline 계산
                spring_baseline_score, spring_baseline_count = calculate_spring_baseline(cluster_id, run_id)
                trend_metadata["spring_baseline"] = spring_baseline_score
                
                # 현재 봄 시즌 데이터 확인
                current_spring_months = []
                for month, count, score in recent_timeseries:
                    # month는 date 객체이므로 month 속성으로 접근
                    month_num = month.month if hasattr(month, 'month') else (month if isinstance(month, int) else None)
                    if month_num and month_num in SPRING_MONTHS:
                        current_spring_months.append((month, float(score or 0)))
                
                if current_spring_months:
                    # 현재 봄 시즌 평균 점수
                    current_spring_score = np.mean([score for _, score in current_spring_months])
                    
                    # spring_adjusted_lift 계산
                    if spring_baseline_score > 0:
                        spring_adjusted_lift = (current_spring_score - spring_baseline_score) / spring_baseline_score
                        trend_metadata["spring_adjusted_lift"] = spring_adjusted_lift
                        
                        # 트렌드 해석
                        trend_status = interpret_seasonal_trend(current_spring_score, spring_baseline_score)
                        trend_metadata["interpretation"] = f"Spring baseline: {spring_baseline_score:.2f}, Current: {current_spring_score:.2f}, Lift: {spring_adjusted_lift:.2%}"
                        return trend_status, trend_metadata
                    else:
                        # Baseline이 없으면 SEASONAL_EXPECTED
                        trend_metadata["interpretation"] = "Spring baseline not available, using SEASONAL_EXPECTED"
                        return "SEASONAL_EXPECTED", trend_metadata
                else:
                    # 현재 봄 시즌이 아니면 SEASONAL_EXPECTED
                    trend_metadata["interpretation"] = "Not in spring season, using SEASONAL_EXPECTED"
                    return "SEASONAL_EXPECTED", trend_metadata
            
            else:
                # 비시즌성 카테고리: 절대 증가 기준
                trend_status = interpret_evergreen_trend(recent_timeseries)
                trend_metadata["interpretation"] = f"Recent avg: {recent_avg:.2f}, Older avg: {older_avg:.2f}"
                return trend_status, trend_metadata
    
    finally:
        conn.close()

def calculate_trend_status(cluster_id: int, run_id: int) -> str:
    """
    Calculate trend status (기존 호환성 유지)
    
    카테고리별 시즌성 해석 로직 적용
    """
    trend_status, _ = calculate_trend_status_with_seasonality(cluster_id, run_id)
    return trend_status

def get_top_clusters_for_briefs(run_id: int, max_briefs: int = 20) -> List[Tuple[int, float, str, Dict[str, Any]]]:
    """
    우선순위 점수 기반으로 상위 N개 클러스터 선정
    
    Returns:
        List of (cluster_id, score, trend_status, trend_metadata)
    """
    conn = get_db_connection()
    cluster_scores = []
    
    try:
        with conn.cursor() as cur:
            # Get all non-noise clusters
            cur.execute("""
                SELECT cluster_id
                FROM clusters
                WHERE created_from_run_id = %s
                AND noise_label = FALSE
            """, (run_id,))
            
            clusters = cur.fetchall()
            logger.info(f"Calculating priority scores for {len(clusters)} clusters")
            
            for (cluster_id,) in clusters:
                score, breakdown = calculate_cluster_priority_score(cluster_id, run_id)
                trend_status, trend_metadata = calculate_trend_status_with_seasonality(cluster_id, run_id)
                
                cluster_scores.append((cluster_id, score, trend_status, trend_metadata))
            
            # Sort by score (descending) and return top N
            cluster_scores.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Top {max_briefs} clusters selected:")
            for i, (cluster_id, score, status, metadata) in enumerate(cluster_scores[:max_briefs], 1):
                category = metadata.get('category', 'unknown')
                logger.info(f"  {i}. Cluster {cluster_id} ({category}): score={score:.2f}, status={status}")
            
            return cluster_scores[:max_briefs]
    
    finally:
        conn.close()

def calculate_scores(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    Calculate scores for all briefs (기존 호환성 유지)
    """
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
                
                # Calculate priority score
                score, breakdown = calculate_cluster_priority_score(cluster_id, run_id)
                
                # Calculate trend status (카테고리별 시즌성 해석 포함)
                trend_status = calculate_trend_status(cluster_id, run_id)
                
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
