#!/usr/bin/env python3
"""
첫 번째 키워드 데이터 저장 및 나머지 키워드 수집 계속 진행
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.config import REDDIT_KEYWORDS
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_and_continue")

# 파이프라인 run 생성
run_id = create_pipeline_run("collect", "running")
logger.info(f"Pipeline run created: run_id={run_id}")

# 첫 번째 키워드: "spring dinner ideas" - 이미 수집 완료
# datasetId: Yu6o5q1FKWhb4jdcH
# 이 데이터는 이미 get-actor-output으로 가져왔으므로 저장만 하면 됨
# (실제로는 별도 스크립트로 저장)

# 나머지 모든 키워드 수집 계속 진행
all_keywords = []
for category, keywords in REDDIT_KEYWORDS.items():
    for keyword in keywords:
        all_keywords.append((category, keyword))

logger.info(f"Total keywords: {len(all_keywords)}")
logger.info(f"First keyword 'spring dinner ideas' already collected (datasetId: Yu6o5q1FKWhb4jdcH)")
logger.info(f"Remaining keywords to collect: {len(all_keywords) - 1}")

# 나머지 키워드들에 대해 Actor 호출 필요
for idx, (category, keyword) in enumerate(all_keywords[1:], 2):  # 첫 번째는 이미 완료
    logger.info(f"[{idx}/{len(all_keywords)}] Need to collect: {category} - {keyword}")
