#!/usr/bin/env python3
"""
모든 수집 완료된 Apify 데이터를 데이터베이스에 저장
MCP 도구를 사용하여 데이터를 가져오고 저장
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_collected_data")

# 확인된 수집 완료 runs
# 각 run의 INPUT에서 키워드를 확인한 후 여기에 추가
COLLECTED_DATASETS = [
    {"datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas"},
    {"datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals"},
    # 나머지 18개 키워드의 dataset ID 추가 필요
]

def save_all_datasets():
    """
    모든 수집 완료된 dataset을 데이터베이스에 저장
    
    주의: 이 스크립트는 MCP 도구를 직접 호출할 수 없으므로,
    실제 저장은 AI Assistant가 MCP 도구를 사용하여 수행해야 합니다.
    """
    logger.info("=" * 60)
    logger.info("수집 완료된 모든 데이터를 데이터베이스에 저장")
    logger.info("=" * 60)
    
    # 파이프라인 run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    total_stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }
    
    # 각 dataset 처리
    for dataset_info in COLLECTED_DATASETS:
        dataset_id = dataset_info["datasetId"]
        keyword = dataset_info["keyword"]
        
        logger.info(f"\nProcessing dataset {dataset_id} for keyword: {keyword}")
        logger.info("→ MCP 도구 mcp_apify_get-actor-output를 사용하여 데이터 가져오기 필요")
        logger.info(f"  datasetId: {dataset_id}")
        logger.info(f"  keyword: {keyword}")
        logger.info(f"  run_id: {run_id}")
    
    logger.info("\n" + "=" * 60)
    logger.info("다음 단계:")
    logger.info("1. 각 dataset의 데이터를 mcp_apify_get-actor-output으로 가져오기")
    logger.info("2. process_apify_results(items, keyword, run_id) 호출하여 저장")
    logger.info("=" * 60)
    
    return run_id

if __name__ == "__main__":
    run_id = save_all_datasets()
    print(f"\nPipeline run_id: {run_id}")
    print("이제 각 dataset의 데이터를 가져와서 저장하세요.")
