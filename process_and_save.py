#!/usr/bin/env python3
"""
수집된 데이터를 처리하여 데이터베이스에 저장
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("process_and_save")

def save_keyword_data(items, keyword, run_id):
    """키워드 데이터 저장"""
    try:
        logger.info(f"Processing {len(items)} items for keyword: {keyword}")
        stats = process_apify_results(items, keyword, run_id)
        logger.info(f"Saved: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
        return stats
    except Exception as e:
        logger.error(f"Error saving data for '{keyword}': {e}", exc_info=True)
        return {"posts_collected": 0, "comments_collected": 0, "errors": [str(e)]}

if __name__ == "__main__":
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run ID: {run_id}")
    
    # 데이터는 MCP를 통해 가져와서 여기에 전달해야 함
    logger.info("Ready to process collected data")
