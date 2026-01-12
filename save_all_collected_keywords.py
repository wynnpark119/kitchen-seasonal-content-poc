#!/usr/bin/env python3
"""
수집 완료된 모든 키워드 데이터를 데이터베이스에 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_collected_keywords")

# 현재까지 확인된 수집 완료 dataset (키워드별)
# 나머지 키워드의 dataset ID는 Apify 콘솔에서 확인 필요
COLLECTED_DATASETS = [
    {"datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas"},
    {"datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals"},
    # 나머지 18개 키워드의 dataset ID 추가 필요:
    # - what to cook in spring
    # - spring meal prep
    # - light spring recipes
    # - spring kitchen decor
    # - kitchen spring refresh
    # - spring table setting ideas
    # - how to decorate kitchen for spring
    # - spring kitchen ideas
    # - refrigerator organization
    # - fridge organization tips
    # - how to organize refrigerator
    # - refrigerator storage ideas
    # - fridge organization system
    # - vegetable prep
    # - how to prep vegetables
    # - vegetable storage tips
    # - how to store vegetables
    # - vegetable washing tips
]

def save_dataset(dataset_id: str, keyword: str, run_id: int):
    """
    단일 dataset의 모든 데이터를 가져와서 데이터베이스에 저장
    
    주의: 이 함수는 MCP 도구를 직접 호출할 수 없으므로,
    AI Assistant가 mcp_apify_get-actor-output을 사용하여
    데이터를 가져온 후 process_apify_results를 호출해야 합니다.
    """
    logger.info(f"Processing dataset {dataset_id} for keyword '{keyword}'...")
    
    # AI Assistant가 mcp_apify_get-actor-output을 사용하여 데이터를 가져와야 함
    # 예시: items = mcp_apify_get-actor-output(datasetId=dataset_id, offset=0, limit=99999)
    # 여기서는 빈 리스트로 가정 (실제 데이터는 AI Assistant가 가져와야 함)
    items = []  # 실제 데이터는 AI Assistant가 가져와서 여기에 채워야 함
    
    stats = process_apify_results(items, keyword, run_id)
    
    logger.info(f"Saved {stats['posts_collected']} posts and {stats['comments_collected']} comments for keyword '{keyword}'.")
    return stats

def main():
    """
    모든 수집 완료된 dataset을 데이터베이스에 저장
    """
    pipeline_run_id = create_pipeline_run("collect_reddit_save_all", status="running")
    logger.info(f"Pipeline run created for saving all collected datasets: run_id={pipeline_run_id}")

    total_stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }

    for dataset_info in COLLECTED_DATASETS:
        try:
            stats = save_dataset(dataset_info["datasetId"], dataset_info["keyword"], pipeline_run_id)
            total_stats["posts_collected"] += stats["posts_collected"]
            total_stats["comments_collected"] += stats["comments_collected"]
            total_stats["keywords_processed"] += 1
            if stats["errors"]:
                total_stats["errors"].extend(stats["errors"])
        except Exception as e:
            logger.error(f"Error saving data for dataset {dataset_info['datasetId']} (keyword: {dataset_info['keyword']}): {e}")
            total_stats["errors"].append(str(e))

    update_pipeline_run(pipeline_run_id, "completed", metadata=total_stats)
    logger.info(f"All datasets saving completed. Total posts: {total_stats['posts_collected']}, comments: {total_stats['comments_collected']}")
    return total_stats

if __name__ == "__main__":
    main()
