#!/usr/bin/env python3
"""
키워드를 배치로 나누어 병렬 수집
- 각 배치당 10개 키워드
- 각 배치당 maxPostsCount 300개
- 여러 배치를 동시에 실행 가능
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

# 모든 키워드 수집
all_keywords = []
for category, keywords in REDDIT_KEYWORDS.items():
    all_keywords.extend(keywords)

# 이미 수집한 키워드 제외
remaining_keywords = [kw for kw in all_keywords if kw not in COLLECTED_KEYWORDS]

# 배치 크기 설정
BATCH_SIZE = 10
MAX_POSTS_PER_BATCH = 300

# 키워드를 배치로 나누기
batches = []
for i in range(0, len(remaining_keywords), BATCH_SIZE):
    batch = remaining_keywords[i:i + BATCH_SIZE]
    batches.append(batch)

print(f"총 {len(remaining_keywords)}개 키워드를 {len(batches)}개 배치로 나눕니다.")
print(f"각 배치당 {BATCH_SIZE}개 키워드, 최대 {MAX_POSTS_PER_BATCH}개 포스트\n")

# 모든 배치에 대한 MCP 호출 정보 출력
print("=" * 80)
print("모든 배치 MCP 호출 (동시 실행 가능)")
print("=" * 80)

for batch_idx, batch in enumerate(batches, 1):
    print(f"\n# 배치 {batch_idx}/{len(batches)}")
    print(f"mcp_apify_call-actor(")
    print(f"    actor='harshmaur/reddit-scraper',")
    print(f"    step='call',")
    print(f"    input={{")
    print(f"        'searchTerms': {batch},")
    print(f"        'searchPosts': True,")
    print(f"        'searchComments': False,")
    print(f"        'crawlCommentsPerPost': True,")
    print(f"        'maxPostsCount': {MAX_POSTS_PER_BATCH},")
    print(f"        'maxCommentsPerPost': 3,")
    print(f"        'fastMode': True,")
    print(f"        'searchSort': 'hot',")
    print(f"        'searchTime': 'all',")
    print(f"        'includeNSFW': False,")
    print(f"        'proxy': {{'useApifyProxy': True, 'apifyProxyGroups': ['RESIDENTIAL']}}")
    print(f"    }}")
    print(f")")
    print()

print("=" * 80)
print(f"총 {len(batches)}개 배치를 동시에 실행할 수 있습니다.")
print("=" * 80)
