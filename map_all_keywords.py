#!/usr/bin/env python3
"""
모든 Reddit scraper runs의 INPUT 확인 및 키워드 매핑
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS, CATEGORIES

# Reddit scraper actor ID
REDDIT_SCRAPER_ACT_ID = "9sHOY9RzPYGjmTHo8"

# 선택된 키워드 목록
selected_keywords = []
for category in CATEGORIES:
    keywords_in_category = REDDIT_KEYWORDS.get(category, [])
    selected_from_category = keywords_in_category[:5]
    selected_keywords.extend(selected_from_category)

print("=" * 60)
print("수집해야 할 키워드 목록 (20개)")
print("=" * 60)
for i, kw in enumerate(selected_keywords, 1):
    print(f"{i}. {kw}")

print("\n" + "=" * 60)
print("현재까지 확인된 Reddit scraper SUCCEEDED runs:")
print("=" * 60)
print("1. FsxHPhDRLkHX7sIIO - 'easy spring meals' (datasetId: hYNaDehMRGFbLd9sW)")
print("2. EDIHhapgDr9MeKuo9 - 'spring dinner ideas' (datasetId: Chej96NJu2xomUrg1)")
print("3. Vi1G5Ja4L8PVWgiHT - 'easy spring meals' (중복, datasetId: doNENk6jt0nsCrqsn)")
print("4. 4X5D3X7BffGQZMRWq - 'spring dinner ideas' (중복, datasetId: CsilDWcwDpLLQQzCP)")

print("\n" + "=" * 60)
print("다음 단계:")
print("=" * 60)
print("나머지 18개 키워드의 runs를 찾기 위해:")
print("1. Apify 콘솔에서 actId='9sHOY9RzPYGjmTHo8'인 모든 SUCCEEDED runs 확인")
print("2. 각 run의 INPUT에서 키워드 확인")
print("3. 키워드별 dataset ID 매핑")
print("4. 모든 dataset의 데이터를 데이터베이스에 저장")

print("\n또는 사용자가 '완료된듯'이라고 했으므로,")
print("사용자에게 나머지 18개 키워드의 dataset ID를 확인하도록 요청할 수 있습니다.")
