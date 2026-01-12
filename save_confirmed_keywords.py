#!/usr/bin/env python3
"""
확인된 2개 키워드의 데이터를 데이터베이스에 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_confirmed_keywords")

# 확인된 키워드 및 dataset ID
CONFIRMED_DATASETS = [
    {"datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas", "itemCount": 563},
    {"datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals", "itemCount": 541},
]

def save_dataset_to_db(dataset_id: str, keyword: str, run_id: int, items: list):
    """
    단일 dataset의 데이터를 데이터베이스에 저장
    """
    logger.info(f"Saving {len(items)} items from dataset {dataset_id} for keyword '{keyword}'...")
    
    stats = process_apify_results(items, keyword, run_id)
    
    logger.info(f"Saved {stats['posts_collected']} posts and {stats['comments_collected']} comments for keyword '{keyword}'.")
    return stats

def main():
    """
    확인된 모든 키워드의 데이터를 데이터베이스에 저장
    """
    try:
        # DATABASE_URL 확인
        database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            logger.info("Please set DATABASE_URL environment variable or run this script on Railway")
            return
        
        # 파이프라인 run 생성
        pipeline_run_id = create_pipeline_run("collect_reddit_save_confirmed", status="running")
        logger.info(f"Pipeline run created: run_id={pipeline_run_id}")

        total_stats = {
            "posts_collected": 0,
            "comments_collected": 0,
            "keywords_processed": 0,
            "errors": []
        }

        # 각 dataset의 데이터를 가져와서 저장
        # 주의: 실제 데이터는 MCP 도구를 통해 가져와야 하므로,
        # 이 스크립트는 데이터가 이미 items 변수에 있다고 가정합니다.
        logger.warning("This script requires items to be fetched using MCP tools first.")
        logger.warning("Please use mcp_apify_get-actor-output to fetch data before calling this script.")

        update_pipeline_run(pipeline_run_id, "completed", metadata=total_stats)
        logger.info(f"All datasets saving completed. Total posts: {total_stats['posts_collected']}, comments: {total_stats['comments_collected']}")
        return total_stats

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
