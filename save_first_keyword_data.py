#!/usr/bin/env python3
"""
첫 번째 키워드 데이터를 데이터베이스에 저장
- Dataset ID: CsilDWcwDpLLQQzCP
- Keyword: spring dinner ideas
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_first_keyword_data")

# 첫 번째 키워드 정보
KEYWORD = "spring dinner ideas"
DATASET_ID = "CsilDWcwDpLLQQzCP"

def save_keyword_data(dataset_id: str, keyword: str):
    """키워드 데이터를 DB에 저장"""
    if not os.getenv("DATABASE_URL"):
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        logger.error("Railway에서 DATABASE_URL을 확인하거나 환경 변수를 설정하세요.")
        return False
    
    # Pipeline run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    # MCP를 통해 데이터 가져오기 (이 스크립트는 수동 실행용)
    logger.info(f"키워드: {KEYWORD}")
    logger.info(f"Dataset ID: {DATASET_ID}")
    logger.info("")
    logger.info("다음 명령으로 데이터를 가져와서 저장하세요:")
    logger.info("  from mcp_apify_get_actor_output import get_actor_output")
    logger.info(f"  items = get_actor_output(dataset_id='{DATASET_ID}', limit=562, offset=0)")
    logger.info(f"  stats = process_apify_results(items, '{KEYWORD}', {run_id})")
    logger.info(f"  update_pipeline_run({run_id}, 'completed', metadata=stats)")
    
    return True

if __name__ == "__main__":
    save_keyword_data(DATASET_ID, KEYWORD)
