#!/usr/bin/env python3
"""
Apify Client SDK를 사용한 병렬 Reddit 수집 (Python 버전)
MCP 대신 직접 Apify API를 호출하여 병렬 실행

실행 방법:
    pip install apify-client
    python collect_parallel_apify_client.py
"""
import asyncio
import json
from datetime import datetime
from apify_client import ApifyClient

# API 토큰으로 클라이언트 초기화
import os
client = ApifyClient(os.getenv('APIFY_API_TOKEN', 'your-apify-api-token-here'))

# 20개 키워드 정의 (카테고리별 5개씩)
KEYWORDS = {
    "SPRING_RECIPES": [
        "spring dinner ideas",
        "easy spring meals",
        "what to cook in spring",
        "spring meal prep",
        "light spring recipes"
    ],
    "SPRING_KITCHEN_STYLING": [
        "spring kitchen decor",
        "kitchen spring refresh",
        "spring table setting ideas",
        "how to decorate kitchen for spring",
        "spring kitchen ideas"
    ],
    "REFRIGERATOR_ORGANIZATION": [
        "refrigerator organization",
        "fridge organization tips",
        "how to organize refrigerator",
        "refrigerator storage ideas",
        "fridge organization system"
    ],
    "VEGETABLE_PREP_HANDLING": [
        "vegetable prep",
        "how to prep vegetables",
        "vegetable storage tips",
        "how to store vegetables",
        "vegetable washing tips"
    ]
}

# 모든 키워드를 flat하게
all_keywords = [kw for category in KEYWORDS.values() for kw in category]

def run_single_scraper(keyword: str):
    """단일 키워드에 대한 Actor 실행"""
    try:
        print(f"✅ 시작: {keyword}")
        
        # fatihtahta/reddit-scraper-search-fast 사용
        run = client.actor('fatihtahta/reddit-scraper-search-fast').call(
            queries=[keyword],
            sort='hot',  # 또는 'top'
            timeframe='all',
            maxPosts=200,
            maxComments=2,
            scrapeComments=True,
            includeNsfw=False
        )
        
        return {
            'keyword': keyword,
            'run_id': run['id'],
            'status': run.get('status', 'UNKNOWN'),
            'dataset_id': run.get('defaultDatasetId'),
            'usage_usd': run.get('usageTotalUsd', 0)
        }
    except Exception as e:
        print(f"❌ 오류 ({keyword}): {e}")
        return {
            'keyword': keyword,
            'error': str(e)
        }

def run_all_scrapers():
    """모든 키워드를 병렬로 실행"""
    print("=" * 60)
    print(f"총 {len(all_keywords)}개 키워드 수집 시작")
    print("=" * 60)
    print()
    
    # 모든 키워드에 대해 Actor 실행 시작 (병렬)
    runs = []
    for keyword in all_keywords:
        run = run_single_scraper(keyword)
        runs.append(run)
    
    print()
    print("=" * 60)
    print(f"총 {len(runs)}개 실행 시작됨")
    print("=" * 60)
    print()
    print("수집 진행 중... (Apify 콘솔에서 진행 상황 확인 가능)")
    print()
    
    # 결과 출력
    print("=" * 60)
    print("실행된 작업 목록:")
    print("=" * 60)
    
    results = []
    for i, run_info in enumerate(runs, 1):
        if 'error' in run_info:
            print(f"{i}. {run_info['keyword']} - ❌ 오류: {run_info['error']}")
        else:
            print(f"{i}. {run_info['keyword']}")
            print(f"   Run ID: {run_info['run_id']}")
            print(f"   Status: {run_info['status']}")
            print(f"   Dataset ID: {run_info['dataset_id']}")
            print(f"   Usage: ${run_info['usage_usd']}")
            print()
            results.append(run_info)
    
    # 결과를 JSON 파일로 저장
    output = {
        'completedAt': datetime.now().isoformat(),
        'totalKeywords': len(all_keywords),
        'successfulRuns': len(results),
        'results': results
    }
    
    with open('collection_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("=" * 60)
    print(f"✅ {len(results)}개 작업이 시작되었습니다.")
    print("결과가 collection_results.json에 저장되었습니다.")
    print("=" * 60)
    print()
    print("참고: 각 Run의 완료 상태는 Apify 콘솔에서 확인하거나")
    print("      get_actor_run() API를 사용하여 확인할 수 있습니다.")

if __name__ == "__main__":
    run_all_scrapers()
