#!/usr/bin/env python3
"""
Reddit scraper runs의 데이터를 데이터베이스에 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_reddit_runs")

# 확인된 Reddit scraper runs (actId: 9sHOY9RzPYGjmTHo8)
REDDIT_RUNS = [
    {"run_id": "FsxHPhDRLkHX7sIIO", "datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals"},
    {"run_id": "EDIHhapgDr9MeKuo9", "datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas"},
]

def save_all_reddit_runs():
    """모든 Reddit scraper runs의 데이터를 저장"""
    logger.info("=" * 60)
    logger.info("Reddit scraper runs 데이터 저장")
    logger.info("=" * 60)
    
    # 파이프라인 run 생성
    pipeline_run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={pipeline_run_id}")
    
    total_stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }
    
    # 각 run 처리
    for run_info in REDDIT_RUNS:
        dataset_id = run_info["datasetId"]
        keyword = run_info["keyword"]
        run_id_str = run_info["run_id"]
        
        logger.info(f"\nProcessing run {run_id_str}: {keyword}")
        logger.info(f"  Dataset ID: {dataset_id}")
        logger.info(f"  Keyword: {keyword}")
        
        # MCP 도구를 사용하여 데이터 가져오기
        # mcp_apify_get-actor-output(datasetId=dataset_id, offset=0, limit=1000)
        # 그 다음 process_apify_results(items, keyword, pipeline_run_id) 호출
    
    logger.info("\n" + "=" * 60)
    logger.info("다음 단계:")
    logger.info("1. 각 dataset의 전체 데이터를 mcp_apify_get-actor-output으로 가져오기")
    logger.info("2. process_apify_results(items, keyword, pipeline_run_id) 호출하여 저장")
    logger.info("=" * 60)
    
    return pipeline_run_id

if __name__ == "__main__":
    run_id = save_all_reddit_runs()
    print(f"\nPipeline run_id: {run_id}")
    print("이제 각 dataset의 데이터를 가져와서 저장하세요.")
