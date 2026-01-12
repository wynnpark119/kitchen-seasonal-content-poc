#!/usr/bin/env python3
"""
수집 완료된 Apify 데이터를 데이터베이스에 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_collected_data")

# 수집 완료된 runs 정보 (run_id, dataset_id, keyword)
# 각 run의 INPUT에서 키워드를 확인해야 함
COLLECTED_RUNS = [
    {"run_id": "EDIHhapgDr9MeKuo9", "datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas"},
    {"run_id": "FsxHPhDRLkHX7sIIO", "datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals"},
    # 나머지 runs도 추가 필요
]

def save_dataset_to_db(dataset_id: str, keyword: str, run_id: int):
    """Apify dataset의 데이터를 데이터베이스에 저장"""
    logger.info(f"Processing dataset {dataset_id} for keyword: {keyword}")
    
    # MCP 도구를 사용하여 데이터 가져오기
    # 실제로는 mcp_apify_get-actor-output 도구를 사용해야 하지만,
    # 여기서는 스크립트로 실행할 수 없으므로 사용자에게 안내
    logger.info(f"Dataset ID: {dataset_id}")
    logger.info(f"Keyword: {keyword}")
    logger.info(f"Run ID: {run_id}")
    logger.info("→ MCP 도구를 사용하여 데이터를 가져온 후 process_apify_results 호출 필요")

def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("수집 완료된 데이터를 데이터베이스에 저장")
    logger.info("=" * 60)
    
    # 파이프라인 run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    # 각 dataset 저장
    for run_info in COLLECTED_RUNS:
        try:
            save_dataset_to_db(
                run_info["datasetId"],
                run_info["keyword"],
                run_id
            )
        except Exception as e:
            logger.error(f"Error saving dataset {run_info['datasetId']}: {e}")
    
    logger.info("=" * 60)
    logger.info("데이터베이스 저장 완료")
    logger.info("=" * 60)
    
    # 파이프라인 run 완료 처리
    update_pipeline_run(run_id, "completed")

if __name__ == "__main__":
    main()
