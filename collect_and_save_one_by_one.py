#!/usr/bin/env python3
"""
20개 키워드를 하나씩 수집하고 적재
- 각 키워드 수집 완료 후 즉시 DB에 적재
- 그 다음 키워드 수집 시작
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS
from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("collect_and_save_one_by_one")

# 카테고리별로 상위 5개씩 선택
selected_keywords = {}
for category, keywords in REDDIT_KEYWORDS.items():
    selected_keywords[category] = keywords[:5]

# 모든 키워드 수집
all_keywords = []
for category, keywords in selected_keywords.items():
    all_keywords.extend(keywords)

# 완료된 키워드 (첫 번째)
completed_keywords = [
    {
        "keyword": "spring dinner ideas",
        "datasetId": "CsilDWcwDpLLQQzCP",
        "runId": "4X5D3X7BffGQZMRWq"
    }
]

print("=" * 60)
print("20개 키워드 하나씩 수집 및 적재")
print("=" * 60)
print(f"총 키워드: {len(all_keywords)}개")
print(f"완료된 키워드: {len(completed_keywords)}개")
print(f"남은 키워드: {len(all_keywords) - len(completed_keywords)}개")
print("=" * 60)

print("\n완료된 키워드:")
for i, kw_info in enumerate(completed_keywords, 1):
    print(f"{i}. {kw_info['keyword']} (Dataset: {kw_info['datasetId']})")

print("\n남은 키워드:")
remaining = [kw for kw in all_keywords if kw not in [c['keyword'] for c in completed_keywords]]
for i, kw in enumerate(remaining, 1):
    print(f"{i}. {kw}")

print("\n" + "=" * 60)
print("다음 단계:")
print("1. 첫 번째 키워드 데이터를 DB에 적재")
print("2. 두 번째 키워드 수집 시작")
print("=" * 60)
