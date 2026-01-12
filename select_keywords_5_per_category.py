#!/usr/bin/env python3
"""
카테고리별 5개씩 키워드 선택
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS

# 카테고리별로 상위 5개씩 선택
selected_keywords = {}

for category, keywords in REDDIT_KEYWORDS.items():
    # 각 카테고리에서 상위 5개만 선택
    selected_keywords[category] = keywords[:5]

print("=" * 60)
print("카테고리별 선택된 키워드 (각 5개씩)")
print("=" * 60)

total_count = 0
for category, keywords in selected_keywords.items():
    print(f"\n[{category}] ({len(keywords)}개)")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw}")
    total_count += len(keywords)

print("\n" + "=" * 60)
print(f"총 선택된 키워드: {total_count}개")
print("=" * 60)

print("\n수집 설정:")
print("  - 총 포스트: 200개 (인기순/추천순)")
print("  - 댓글: 포스트당 2개씩 (인기순)")
print("  - 정렬: hot 또는 top")

print("\n선택된 키워드 전체 목록:")
all_selected = []
for category, keywords in selected_keywords.items():
    all_selected.extend(keywords)

for i, kw in enumerate(all_selected, 1):
    print(f"{i}. {kw}")
