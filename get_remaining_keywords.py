#!/usr/bin/env python3
"""
현재 실행 중인 키워드를 제외한 나머지 키워드 목록 생성
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS

# 이미 수집 완료된 키워드
COLLECTED_KEYWORDS = [
    "spring dinner ideas",
    "easy spring meals"
]

# 현재 실행 중인 키워드 (확인된 것들)
RUNNING_KEYWORDS = [
    "what to cook in spring",
    "spring meal prep",
    "light spring recipes",
    "quick spring dinner",
    "spring weeknight meals",
    "healthy spring meals",
    "what do you cook in spring",
    "best spring dinner ideas",
    "spring kitchen decor",
    "kitchen spring refresh",
    "spring kitchen curtains",
    "spring kitchen art",
    "how do you decorate your kitchen for spring",
    "what spring decor do you use in kitchen",
    "anyone else refresh kitchen for spring",
    "best way to style kitchen for spring",
    "what spring colors work in kitchen",
    "how do you make kitchen feel spring",
    "refrigerator organization",
    "fridge organization tips"
]

# 모든 키워드 수집
all_keywords = []
for category, keywords in REDDIT_KEYWORDS.items():
    all_keywords.extend(keywords)

# 이미 수집한 키워드 + 현재 실행 중인 키워드 제외
remaining_keywords = [
    kw for kw in all_keywords 
    if kw not in COLLECTED_KEYWORDS and kw not in RUNNING_KEYWORDS
]

print(f"총 키워드: {len(all_keywords)}개")
print(f"이미 수집 완료: {len(COLLECTED_KEYWORDS)}개")
print(f"현재 실행 중: {len(RUNNING_KEYWORDS)}개")
print(f"남은 키워드: {len(remaining_keywords)}개\n")

print("남은 키워드 목록:")
for i, kw in enumerate(remaining_keywords, 1):
    print(f"{i}. {kw}")
