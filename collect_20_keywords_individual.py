#!/usr/bin/env python3
"""
카테고리별 5개씩 선택된 20개 키워드를 각각 개별 run으로 수집
- 각 키워드당 200개 포스트
- 댓글: 포스트당 2개씩 (인기순)
- 정렬: hot (인기순)
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS

# 카테고리별로 상위 5개씩 선택
selected_keywords = {}
for category, keywords in REDDIT_KEYWORDS.items():
    selected_keywords[category] = keywords[:5]

# 모든 키워드 수집
all_keywords = []
for category, keywords in selected_keywords.items():
    all_keywords.extend(keywords)

print("=" * 60)
print("수집 설정")
print("=" * 60)
print(f"총 키워드: {len(all_keywords)}개")
print(f"각 키워드당 포스트: 200개")
print(f"댓글: 포스트당 2개씩 (인기순)")
print(f"정렬: hot (인기순)")
print("=" * 60)

print("\n키워드 목록:")
for i, kw in enumerate(all_keywords, 1):
    print(f"{i:2d}. {kw}")

print("\n" + "=" * 60)
print("각 키워드별 MCP 호출 예시:")
print("=" * 60)
print("\n첫 번째 키워드 예시:")
print(f"mcp_apify_call-actor(")
print(f"    actor='harshmaur/reddit-scraper',")
print(f"    step='call',")
print(f"    input={{")
print(f"        'searchTerms': ['{all_keywords[0]}'],")
print(f"        'searchPosts': True,")
print(f"        'searchComments': False,")
print(f"        'crawlCommentsPerPost': True,")
print(f"        'maxPostsCount': 200,")
print(f"        'maxCommentsPerPost': 2,")
print(f"        'fastMode': True,")
print(f"        'searchSort': 'hot',")
print(f"        'searchTime': 'all',")
print(f"        'includeNSFW': False,")
print(f"        'proxy': {{'useApifyProxy': True, 'apifyProxyGroups': ['RESIDENTIAL']}}")
print(f"    }}")
print(f")")
