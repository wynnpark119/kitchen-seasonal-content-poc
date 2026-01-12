#!/usr/bin/env python3
"""
22개 run의 데이터를 데이터베이스에 저장
각 run의 INPUT에서 키워드를 확인하고 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_22_runs")

# 22개 run ID 목록
RUN_IDS = [
    "FsxHPhDRLkHX7sIIO",
    "EDIHhapgDr9MeKuo9",
    "B4ZGgle4f7Sxn57oj",
    "rB02EjeA284GIGdBv",
    "E5Wbeu9qZNPdmHVde",
    "H2i9r1n72nDK6tKqE",
    "S9XXqLOuqT07VjbIO",
    "YLQ3LfWGq68FI0WJa",
    "OMVaruQKYhfzdLG6v",
    "3LLkEW4ia8f8icL61",
    "AuZYh2r54y1VuKllj",
    "Y3JPschU2EeyBRj1R",
    "rhS5MhGU6PmqGTFwc",
    "YeeFQm8dzaMqT8anf",
    "QWPru6wp0nukBGfs6",
    "D5k1JLKOHb8nygUdu",
    "d6EZ7ZhMLVwBeOnui",
    "x2ZxITDo9d3fTqRXi",
    "erqL8O8QBXS99P1Yd",
    "g3JL67O7G6Dhw0OFj",
    "F0IQtYzT3xHn9BKTi",
    "MRGTSEIJJGP6zP4vi",
]

# harshmaur/reddit-scraper actor ID
REDDIT_SCRAPER_ACT_ID = "9sHOY9RzPYGjmTHo8"

def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("22개 run의 데이터를 데이터베이스에 저장")
    logger.info("=" * 60)
    
    # 파이프라인 run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    # 각 run 처리
    reddit_runs = []
    for run_id_str in RUN_IDS:
        logger.info(f"\nProcessing run: {run_id_str}")
        logger.info("→ Run 정보 확인 필요 (MCP 도구 사용)")
        logger.info("→ INPUT에서 키워드 확인 필요")
        logger.info("→ Dataset ID 확인 필요")
        reddit_runs.append(run_id_str)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"총 {len(reddit_runs)}개 run 처리 예정")
    logger.info("=" * 60)
    
    return run_id

if __name__ == "__main__":
    run_id = main()
    print(f"\nPipeline run_id: {run_id}")
    print("이제 각 run의 데이터를 가져와서 저장하세요.")
