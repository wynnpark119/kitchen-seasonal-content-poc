#!/usr/bin/env python3
"""
첫 번째 키워드 데이터를 데이터베이스에 적재
"""
import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_first_keyword")

# 첫 번째 키워드 정보
KEYWORD = "spring dinner ideas"
DATASET_ID = "CsilDWcwDpLLQQzCP"

def main():
    """메인 함수"""
    if not os.getenv("DATABASE_URL"):
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        logger.error("환경 변수를 설정하거나 Railway에서 DATABASE_URL을 확인하세요.")
        return
    
    # Pipeline run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    logger.info(f"키워드: {KEYWORD}")
    logger.info(f"Dataset ID: {DATASET_ID}")
    logger.info("MCP를 통해 데이터를 가져와서 저장하세요:")
    logger.info(f"  mcp_apify_get-actor-output(datasetId='{DATASET_ID}', limit=562, offset=0)")
    logger.info(f"  그 다음 process_apify_results(items, '{KEYWORD}', {run_id})")

if __name__ == "__main__":
    main()
