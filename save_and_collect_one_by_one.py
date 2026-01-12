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

logger = setup_logger("save_and_collect_one_by_one")

# 카테고리별로 상위 5개씩 선택
selected_keywords = {}
for category, keywords in REDDIT_KEYWORDS.items():
    selected_keywords[category] = keywords[:5]

# 모든 키워드 수집
all_keywords = []
for category, keywords in selected_keywords.items():
    all_keywords.extend(keywords)

print("=" * 60)
print("20개 키워드 하나씩 수집 및 적재")
print("=" * 60)
print(f"총 키워드: {len(all_keywords)}개")
print(f"각 키워드당 포스트: 200개")
print(f"댓글: 포스트당 2개씩")
print("=" * 60)

print("\n키워드 목록:")
for i, kw in enumerate(all_keywords, 1):
    print(f"{i:2d}. {kw}")

print("\n" + "=" * 60)
print("작업 순서:")
print("1. 각 키워드 수집 (MCP 호출)")
print("2. 수집 완료 후 데이터베이스에 적재")
print("3. 다음 키워드로 진행")
print("=" * 60)
