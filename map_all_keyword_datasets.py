#!/usr/bin/env python3
"""
모든 Reddit scraper runs 확인 및 키워드-데이터셋 ID 매핑
MCP 도구를 사용하여 모든 runs를 확인하고 INPUT을 가져옵니다.
"""
import json

# Reddit scraper actor ID
REDDIT_SCRAPER_ACT_ID = "9sHOY9RzPYGjmTHo8"

# 현재까지 확인된 runs (run_id, store_id, dataset_id)
KNOWN_RUNS = [
    {"run_id": "FsxHPhDRLkHX7sIIO", "store_id": "y6jHTC40klvlCK8Jd", "dataset_id": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals"},
    {"run_id": "EDIHhapgDr9MeKuo9", "store_id": "fWU9LnH1a4zbhPxTy", "dataset_id": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas"},
    {"run_id": "Vi1G5Ja4L8PVWgiHT", "store_id": "X0TIaw56DgIoLeNEj", "dataset_id": "doNENk6jt0nsCrqsn", "keyword": "easy spring meals"},
    {"run_id": "4X5D3X7BffGQZMRWq", "store_id": "J8T6Sskm6e4bTlzu9", "dataset_id": "CsilDWcwDpLLQQzCP", "keyword": "spring dinner ideas"},
]

print("=" * 60)
print("현재까지 확인된 Reddit scraper runs")
print("=" * 60)
for i, run in enumerate(KNOWN_RUNS, 1):
    print(f"{i}. {run['keyword']}")
    print(f"   Run ID: {run['run_id']}")
    print(f"   Dataset ID: {run['dataset_id']}")
    print()

print("=" * 60)
print("다음 단계:")
print("=" * 60)
print("모든 SUCCEEDED runs를 확인하여 Reddit scraper runs (actId: 9sHOY9RzPYGjmTHo8)를 찾고,")
print("각 run의 INPUT을 확인하여 키워드-데이터셋 ID 매핑을 완료합니다.")
