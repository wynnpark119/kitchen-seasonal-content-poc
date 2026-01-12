#!/usr/bin/env python3
"""
로컬에서 빠르게 실행하는 병렬 Reddit 수집 스크립트
Apify Client SDK를 사용하여 20개 키워드를 병렬로 수집
"""
import sys
import os
import json
from pathlib import Path
from apify_client import ApifyClient

# API 토큰 설정
APIFY_TOKEN = os.getenv('APIFY_API_TOKEN', 'your-apify-api-token-here')

# 20개 키워드 정의
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

# 모든 키워드
all_keywords = [kw for category in KEYWORDS.values() for kw in category]

def main():
    """메인 함수"""
    print("=" * 60)
    print("로컬 병렬 Reddit 수집 시작")
    print("=" * 60)
    print(f"총 키워드: {len(all_keywords)}개")
    print()
    
    # Apify Client 초기화
    client = ApifyClient(APIFY_TOKEN)
    
    # 병렬로 모든 키워드에 대해 Actor 실행 시작
    runs = []
    run_keyword_map = {}
    
    print("키워드별 Run 시작 중...")
    print("-" * 60)
    
    for keyword in all_keywords:
        try:
            print(f"시작: {keyword}")
            
            # fatihtahta/reddit-scraper-search-fast 사용
            run = client.actor('fatihtahta/reddit-scraper-search-fast').call(
                queries=[keyword],
                sort='hot',
                timeframe='all',
                maxPosts=200,
                maxComments=2,
                scrapeComments=True,
                includeNsfw=False
            )
            
            runs.append(run)
            run_keyword_map[run['id']] = keyword
            print(f"  ✅ Run ID: {run['id']}")
            print()
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            print()
    
    print("=" * 60)
    print(f"총 {len(runs)}개 Run 시작 완료!")
    print("=" * 60)
    print()
    print("Apify 콘솔에서 진행 상황 확인:")
    print("https://console.apify.com")
    print()
    
    # 결과 저장
    results = []
    for run_id, keyword in run_keyword_map.items():
        results.append({
            'keyword': keyword,
            'runId': run_id,
            'status': 'RUNNING',
            'consoleUrl': f'https://console.apify.com/view/runs/{run_id}'
        })
    
    output = {
        'startedAt': str(Path(__file__).stat().st_mtime),
        'totalKeywords': len(all_keywords),
        'runsStarted': len(runs),
        'results': results
    }
    
    with open('collection_runs_started.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("=" * 60)
    print("✅ 모든 Run 시작 완료!")
    print("=" * 60)
    print()
    print("결과가 collection_runs_started.json에 저장되었습니다.")
    print()
    print("각 Run의 완료 상태는 Apify 콘솔에서 확인하세요:")
    for result in results:
        print(f"  - {result['keyword']}: {result['consoleUrl']}")

if __name__ == "__main__":
    main()
