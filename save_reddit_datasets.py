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

logger = setup_logger("save_reddit_datasets")

# 확인된 Reddit scraper runs (actId: 9sHOY9RzPYGjmTHo8)
REDDIT_DATASETS = [
    {"datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals", "itemCount": 541},
    {"datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas", "itemCount": 563},
]

def save_dataset_to_db(dataset_id: str, keyword: str, item_count: int, pipeline_run_id: int):
    """
    단일 dataset의 모든 데이터를 가져와서 데이터베이스에 저장
    
    주의: 이 함수는 MCP 도구를 직접 호출할 수 없으므로,
    실제 저장은 AI Assistant가 MCP 도구를 사용하여 수행해야 합니다.
    """
    logger.info(f"Processing dataset {dataset_id} for keyword: {keyword}")
    logger.info(f"  Total items: {itemCount}")
    logger.info(f"  Pipeline run ID: {pipeline_run_id}")
    
    # MCP 도구를 사용하여 전체 데이터 가져오기
    # mcp_apify_get-actor-output(datasetId=dataset_id, offset=0, limit=item_count)
    # 그 다음 process_apify_results(items, keyword, pipeline_run_id) 호출

def main():
    """메인 함수"""
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
    
    # 각 dataset 처리
    for dataset_info in REDDIT_DATASETS:
        dataset_id = dataset_info["datasetId"]
        keyword = dataset_info["keyword"]
        item_count = dataset_info["itemCount"]
        
        logger.info(f"\nProcessing dataset {dataset_id} for keyword: {keyword}")
        logger.info(f"  Total items: {item_count}")
        save_dataset_to_db(dataset_id, keyword, item_count, pipeline_run_id)
    
    logger.info("\n" + "=" * 60)
    logger.info("다음 단계:")
    logger.info("1. 각 dataset의 전체 데이터를 mcp_apify_get-actor-output으로 가져오기")
    logger.info("2. process_apify_results(items, keyword, pipeline_run_id) 호출하여 저장")
    logger.info("=" * 60)
    
    return pipeline_run_id

if __name__ == "__main__":
    run_id = main()
    print(f"\nPipeline run_id: {run_id}")
    print("이제 각 dataset의 데이터를 가져와서 저장하세요.")
