#!/usr/bin/env python3
"""
이미 수집한 키워드를 제외한 나머지 키워드만 병렬로 수집
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

print(f"총 {len(all_keywords)}개 키워드 중")
print(f"이미 수집 완료: {len(COLLECTED_KEYWORDS)}개")
print(f"  - {COLLECTED_KEYWORDS[0]}")
print(f"  - {COLLECTED_KEYWORDS[1]}")
print(f"\n남은 키워드: {len(remaining_keywords)}개")
print(f"\n키워드 목록:")
for i, kw in enumerate(remaining_keywords, 1):
    print(f"  {i}. {kw}")

print(f"\n\nMCP 호출 예시:")
print(f"mcp_apify_call-actor(")
print(f"    actor='harshmaur/reddit-scraper',")
print(f"    step='call',")
print(f"    input={{")
print(f"        'searchTerms': {remaining_keywords},")
print(f"        'searchPosts': True,")
print(f"        'searchComments': False,")
print(f"        'crawlCommentsPerPost': True,")
print(f"        'maxPostsCount': 900,")
print(f"        'maxCommentsPerPost': 3,")
print(f"        'fastMode': True,")
print(f"        'searchSort': 'hot',")
print(f"        'searchTime': 'all',")
print(f"        'includeNSFW': False,")
print(f"        'proxy': {{'useApifyProxy': True, 'apifyProxyGroups': ['RESIDENTIAL']}}")
print(f"    }}")
print(f")")
