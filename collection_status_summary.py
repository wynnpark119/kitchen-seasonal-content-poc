#!/usr/bin/env python3
"""
키워드 수집 조건 및 현재 상태 요약
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS, MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST

# 카테고리별로 상위 5개씩 선택
selected_keywords = {}
for category, keywords in REDDIT_KEYWORDS.items():
    selected_keywords[category] = keywords[:5]

# 모든 키워드 수집
all_keywords = []
for category, keywords in selected_keywords.items():
    all_keywords.extend(keywords)

# 완료된 키워드 (수집 완료)
completed_keywords = [
    {
        "keyword": "spring dinner ideas",
        "datasetId": "CsilDWcwDpLLQQzCP",
        "runId": "4X5D3X7BffGQZMRWq",
        "items": 562
    },
    {
        "keyword": "easy spring meals",
        "datasetId": "doNENk6jt0nsCrqsn",
        "runId": "Vi1G5Ja4L8PVWgiHT",
        "items": 538
    },
    {
        "keyword": "what to cook in spring",
        "datasetId": "qIcNnHR7HwY2oknbp",
        "runId": "DraJI7MBrnRjKDFXe",
        "items": 27
    }
]

completed_keyword_list = [kw["keyword"] for kw in completed_keywords]
remaining_keywords = [kw for kw in all_keywords if kw not in completed_keyword_list]

print("=" * 70)
print("키워드 수집 조건 및 현재 상태")
print("=" * 70)

print("\n📋 수집 조건:")
print(f"  • 각 키워드당 포스트: 200개 (실제 사용)")
print(f"  • 댓글: 포스트당 2개씩 (인기순, 실제 사용)")
print(f"  • 정렬: hot (인기순)")
print(f"  • 검색 기간: all (전체 기간)")
print(f"  • NSFW 제외: True")
print(f"  • Proxy: Apify Residential Proxy")
print(f"\n  ⚠️  참고: config.py에는 {MAX_POSTS_PER_KEYWORD}개, {TOP_COMMENTS_PER_POST}개로 설정되어 있으나,")
print(f"     실제 수집은 200개 포스트, 2개 댓글로 진행되었습니다.")

print("\n📊 카테고리별 키워드 (각 5개씩):")
for category, keywords in selected_keywords.items():
    print(f"\n  [{category}]")
    for i, kw in enumerate(keywords, 1):
        status = "✅ 완료" if kw in completed_keyword_list else "⏳ 대기"
        print(f"    {i}. {kw} {status}")

print("\n" + "=" * 70)
print("수집 현황")
print("=" * 70)
print(f"총 키워드: {len(all_keywords)}개")
print(f"완료: {len(completed_keywords)}개")
print(f"남은 키워드: {len(remaining_keywords)}개")
print(f"진행률: {len(completed_keywords)}/{len(all_keywords)} ({len(completed_keywords)*100//len(all_keywords)}%)")

print("\n✅ 완료된 키워드:")
for i, kw_info in enumerate(completed_keywords, 1):
    print(f"  {i}. {kw_info['keyword']}")
    print(f"     Dataset: {kw_info['datasetId']}")
    print(f"     Run ID: {kw_info['runId']}")
    print(f"     수집된 아이템: {kw_info['items']}개")

print("\n⏳ 남은 키워드:")
for i, kw in enumerate(remaining_keywords, 1):
    print(f"  {i}. {kw}")

print("\n" + "=" * 70)
print("다음 수집 시 사용할 설정:")
print("=" * 70)
print("""
{
    'searchTerms': ['키워드'],
    'searchPosts': True,
    'searchComments': False,
    'crawlCommentsPerPost': True,
    'maxPostsCount': 200,
    'maxCommentsPerPost': 2,
    'fastMode': True,
    'searchSort': 'hot',
    'searchTime': 'all',
    'includeNSFW': False,
    'proxy': {
        'useApifyProxy': True,
        'apifyProxyGroups': ['RESIDENTIAL']
    }
}
""")
