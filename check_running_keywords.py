#!/usr/bin/env python3
"""
실행 중인 run들의 키워드 중복 확인
"""
import json
from collections import Counter

# 확인된 키워드들 (INPUT에서 확인한 것들)
confirmed_keywords = {
    # 배치로 실행된 것들 (10개씩)
    "batch_1": ["what to cook in spring", "spring meal prep", "light spring recipes", "quick spring dinner", "spring weeknight meals", "healthy spring meals", "what do you cook in spring", "best spring dinner ideas", "spring kitchen decor", "kitchen spring refresh"],
    "batch_2": ["spring kitchen curtains", "spring kitchen art", "how do you decorate your kitchen for spring", "what spring decor do you use in kitchen", "anyone else refresh kitchen for spring", "best way to style kitchen for spring", "what spring colors work in kitchen", "how do you make kitchen feel spring", "refrigerator organization", "fridge organization tips"],
    
    # 개별로 실행된 것들
    "individual_1": ["kitchen spring refresh"],
    "individual_2": ["spring kitchen decor"],
    "individual_3": ["best spring dinner ideas"],
    "individual_4": ["what do you cook in spring"],
    "individual_5": ["healthy spring meals"],
}

# 모든 키워드 수집
all_keywords_list = []
for batch_name, keywords in confirmed_keywords.items():
    all_keywords_list.extend(keywords)

# 중복 확인
keyword_counts = Counter(all_keywords_list)
duplicates = {kw: count for kw, count in keyword_counts.items() if count > 1}

print("=" * 60)
print("실행 중인 키워드 분석")
print("=" * 60)
print(f"\n총 확인된 키워드: {len(all_keywords_list)}개")
print(f"고유 키워드: {len(set(all_keywords_list))}개")
print(f"중복 키워드: {len(duplicates)}개")

if duplicates:
    print("\n⚠️ 중복된 키워드:")
    for kw, count in duplicates.items():
        print(f"  - '{kw}': {count}번 실행 중")
else:
    print("\n✅ 중복 없음")

print("\n" + "=" * 60)
print("현재 실행 중인 키워드 목록:")
print("=" * 60)
for kw in sorted(set(all_keywords_list)):
    print(f"  - {kw}")
