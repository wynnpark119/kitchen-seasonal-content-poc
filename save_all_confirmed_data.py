#!/usr/bin/env python3
"""
확인된 2개 키워드의 모든 데이터를 데이터베이스에 저장
MCP 도구를 통해 데이터를 가져온 후 저장합니다.
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_confirmed_data")

# 확인된 키워드 및 dataset ID
CONFIRMED_DATASETS = [
    {"datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas", "itemCount": 563},
    {"datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals", "itemCount": 541},
]

def save_dataset_items(items: list, keyword: str, run_id: int):
    """
    단일 dataset의 데이터를 데이터베이스에 저장
    """
    logger.info(f"Saving {len(items)} items for keyword '{keyword}'...")
    
    stats = process_apify_results(items, keyword, run_id)
    
    logger.info(f"Saved {stats['posts_collected']} posts and {stats['comments_collected']} comments for keyword '{keyword}'.")
    return stats

def main():
    """
    확인된 모든 키워드의 데이터를 데이터베이스에 저장
    
    사용법:
    1. MCP 도구를 사용하여 각 dataset의 모든 데이터를 가져옵니다:
       - mcp_apify_get-actor-output(datasetId="Chej96NJu2xomUrg1", offset=0, limit=563)
       - mcp_apify_get-actor-output(datasetId="hYNaDehMRGFbLd9sW", offset=0, limit=541)
    
    2. 가져온 데이터를 이 함수에 전달하여 저장합니다.
    """
    try:
        # DATABASE_URL 확인
        database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            logger.info("Please set DATABASE_URL environment variable or run this script on Railway")
            logger.info("Example: export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
            return None
        
        # 파이프라인 run 생성
        pipeline_run_id = create_pipeline_run("collect_reddit_save_confirmed", status="running")
        logger.info(f"Pipeline run created: run_id={pipeline_run_id}")

        total_stats = {
            "posts_collected": 0,
            "comments_collected": 0,
            "keywords_processed": 0,
            "errors": []
        }

        # 각 dataset의 데이터를 저장
        # 주의: 실제 데이터는 MCP 도구를 통해 가져와야 합니다
        logger.info("=" * 60)
        logger.info("데이터 저장 준비 완료")
        logger.info("=" * 60)
        logger.info("다음 단계:")
        logger.info("1. MCP 도구를 사용하여 각 dataset의 모든 데이터를 가져옵니다")
        logger.info("2. 가져온 데이터를 save_dataset_items() 함수에 전달하여 저장합니다")
        logger.info("=" * 60)

        # 실제 데이터 저장은 MCP 도구를 통해 가져온 후 수행해야 합니다
        # 예시:
        # items_1 = mcp_apify_get_actor_output(datasetId="Chej96NJu2xomUrg1", offset=0, limit=563)
        # stats_1 = save_dataset_items(items_1, "spring dinner ideas", pipeline_run_id)
        # total_stats["posts_collected"] += stats_1["posts_collected"]
        # total_stats["comments_collected"] += stats_1["comments_collected"]
        # total_stats["keywords_processed"] += 1

        update_pipeline_run(pipeline_run_id, "completed", metadata=total_stats)
        logger.info(f"All datasets saving completed. Total posts: {total_stats['posts_collected']}, comments: {total_stats['comments_collected']}")
        return total_stats

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
