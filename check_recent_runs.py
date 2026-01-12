#!/usr/bin/env python3
"""
최근 성공한 Apify runs 확인 및 키워드 추출
"""
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 최근 성공한 runs (actId: 9sHOY9RzPYGjmTHo8 = harshmaur/reddit-scraper)
recent_succeeded_runs = [
    {"id": "FsxHPhDRLkHX7sIIO", "datasetId": "hYNaDehMRGFbLd9sW"},
    {"id": "EDIHhapgDr9MeKuo9", "datasetId": "Chej96NJu2xomUrg1"},
]

print("=" * 60)
print("최근 성공한 Reddit 수집 Runs")
print("=" * 60)

for i, run in enumerate(recent_succeeded_runs, 1):
    print(f"\n{i}. Run ID: {run['id']}")
    print(f"   Dataset ID: {run['datasetId']}")
    
    # Key-value store에서 INPUT 확인
    # (실제로는 MCP 도구를 사용해야 하지만, 여기서는 정보만 출력)
    print(f"   → INPUT 확인 필요 (key-value store)")

print("\n" + "=" * 60)
print("다음 단계:")
print("1. 각 run의 INPUT에서 키워드 확인")
print("2. Dataset에서 데이터 가져오기")
print("3. 데이터베이스에 저장")
print("=" * 60)
