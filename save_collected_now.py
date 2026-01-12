#!/usr/bin/env python3
"""
수집 완료된 데이터를 즉시 데이터베이스에 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_collected_now")

# 수집 완료된 키워드 정보
COLLECTED_KEYWORDS = [
    {
        "keyword": "spring dinner ideas",
        "datasetId": "Yu6o5q1FKWhb4jdcH",
        "total_items": 889
    },
    {
        "keyword": "easy spring meals",
        "datasetId": "BdiwpZTKHdd7SATso",
        "total_items": 830
    }
]

def main():
    """메인 함수"""
    if not os.getenv("DATABASE_URL"):
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        return
    
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    logger.info("MCP를 통해 데이터를 가져와서 저장하세요:")
    for kw in COLLECTED_KEYWORDS:
        logger.info(f"\n키워드: {kw['keyword']}")
        logger.info(f"  Dataset ID: {kw['datasetId']}")
        logger.info(f"  MCP 호출: mcp_apify_get_actor_output(datasetId='{kw['datasetId']}', limit={kw['total_items']}, offset=0)")
        logger.info(f"  저장: process_apify_results(items, '{kw['keyword']}', {run_id})")

if __name__ == "__main__":
    main()
