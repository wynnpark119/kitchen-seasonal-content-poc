"""
Reddit data collection via Apify Client SDK (병렬 실행)
Railway Worker에서 실행되는 병렬 수집 모듈
"""
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from apify_client import ApifyClient
from .config import MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST, REDDIT_KEYWORDS
from .db import create_pipeline_run, update_pipeline_run, upsert_reddit_post, upsert_reddit_comment
from .logging import setup_logger
from .process_apify_results import process_apify_results

logger = setup_logger("collect_reddit_parallel")

def collect_reddit_data_parallel(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    Apify Client SDK를 사용하여 모든 키워드를 병렬로 수집
    
    Args:
        run_id: Pipeline run ID
        dry_run: If True, skip actual collection
        
    Returns:
        수집 통계 정보
    """
    stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "runs_started": 0,
        "runs_completed": 0,
        "errors": []
    }
    
    # Apify API 토큰 확인
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        error_msg = "APIFY_API_TOKEN 환경 변수가 설정되지 않았습니다."
        logger.error(error_msg)
        stats["errors"].append(error_msg)
        return stats
    
    # Apify Client 초기화
    client = ApifyClient(apify_token)
    
    # 카테고리별로 상위 5개씩 선택
    selected_keywords = {}
    for category, keywords in REDDIT_KEYWORDS.items():
        selected_keywords[category] = keywords[:5]
    
    # 모든 키워드 수집
    all_keywords = []
    for category, keywords in selected_keywords.items():
        all_keywords.extend(keywords)
    
    logger.info(f"Starting parallel Reddit collection for {len(all_keywords)} keywords")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would collect up to 200 posts per keyword")
        logger.info(f"[DRY RUN] Total keywords: {len(all_keywords)}")
        stats["keywords_processed"] = len(all_keywords)
        return stats
    
    # 병렬로 모든 키워드에 대해 Actor 실행 시작
    runs = []
    run_keyword_map = {}
    
    for keyword in all_keywords:
        try:
            logger.info(f"Starting collection for keyword: {keyword}")
            
            # fatihtahta/reddit-scraper-search-fast 사용
            # 실제 수집 조건: 200개 포스트, 2개 댓글
            run = client.actor('fatihtahta/reddit-scraper-search-fast').call(
                queries=[keyword],
                sort='hot',
                timeframe='all',
                maxPosts=200,  # 실제 사용 조건
                maxComments=2,  # 실제 사용 조건
                scrapeComments=True,
                includeNsfw=False
            )
            
            runs.append(run)
            run_keyword_map[run['id']] = keyword
            stats["runs_started"] += 1
            
            logger.info(f"✅ Started: {keyword} (Run ID: {run['id']})")
            
        except Exception as e:
            error_msg = f"Error starting collection for '{keyword}': {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
    
    logger.info(f"Started {stats['runs_started']} parallel runs")
    
    # 각 Run의 완료를 기다리고 데이터 수집
    for run in runs:
        run_id_apify = run['id']
        keyword = run_keyword_map[run_id_apify]
        
        try:
            logger.info(f"Waiting for completion: {keyword} (Run ID: {run_id_apify})")
            
            # Run 완료 대기
            finished_run = client.run(run_id_apify).wait_for_finish()
            
            if finished_run.get('status') == 'SUCCEEDED':
                dataset_id = finished_run.get('defaultDatasetId')
                logger.info(f"✅ Completed: {keyword} (Dataset ID: {dataset_id})")
                
                # Dataset에서 데이터 가져오기
                dataset_items = []
                for item in client.dataset(dataset_id).iterate_items():
                    dataset_items.append(item)
                
                logger.info(f"Retrieved {len(dataset_items)} items for {keyword}")
                
                # 데이터 처리 및 저장
                result_stats = process_apify_results(dataset_items, keyword, run_id)
                stats["posts_collected"] += result_stats["posts_collected"]
                stats["comments_collected"] += result_stats["comments_collected"]
                stats["keywords_processed"] += 1
                stats["runs_completed"] += 1
                
                if result_stats["errors"]:
                    stats["errors"].extend(result_stats["errors"])
                    
            else:
                error_msg = f"Run failed for '{keyword}': {finished_run.get('status')}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
                
        except Exception as e:
            error_msg = f"Error processing run for '{keyword}': {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
    
    logger.info(f"Parallel collection completed: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
    logger.info(f"Runs: {stats['runs_completed']}/{stats['runs_started']} completed")
    
    return stats
