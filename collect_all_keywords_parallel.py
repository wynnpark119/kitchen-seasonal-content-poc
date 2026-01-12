#!/usr/bin/env python3
"""
모든 키워드를 병렬로 수집하는 스크립트
Apify Actor의 searchTerms 배열에 모든 키워드를 전달하여 병렬 수집
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS

# 모든 키워드 수집
all_keywords = []
for category, keywords in REDDIT_KEYWORDS.items():
    all_keywords.extend(keywords)

print(f"총 {len(all_keywords)}개 키워드를 병렬로 수집합니다.")
print(f"\n키워드 목록:")
for i, kw in enumerate(all_keywords, 1):
    print(f"  {i}. {kw}")

print(f"\n\nMCP 호출 예시:")
print(f"mcp_apify_call-actor(")
print(f"    actor='harshmaur/reddit-scraper',")
print(f"    step='call',")
print(f"    input={{")
print(f"        'searchTerms': {all_keywords},")
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
