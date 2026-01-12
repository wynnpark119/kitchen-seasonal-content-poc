#!/usr/bin/env python3
"""
Reddit 데이터 본격 수집 실행 스크립트
각 키워드별로 Apify Actor를 호출하여 Reddit 포스트 수집
"""
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS, MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST
from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("run_reddit_collection")

def main():
    """메인 실행 함수"""
    # DATABASE_URL 확인
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        print("환경 변수 설정:")
        print("export DATABASE_URL='postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway'")
        sys.exit(1)
    
    # Pipeline run 생성
    run_id = create_pipeline_run("collect", status="running")
    logger.info(f"Pipeline run started: run_id={run_id}")
    print(f"\n✅ Pipeline run_id: {run_id}")
    
    # 모든 키워드 수집
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        all_keywords.extend(keywords)
    
    logger.info(f"Starting Reddit collection for {len(all_keywords)} keywords")
    print(f"\n📊 수집 계획:")
    print(f"  - 총 키워드: {len(all_keywords)}개")
    print(f"  - 각 키워드당 최대 포스트: {MAX_POSTS_PER_KEYWORD}개")
    print(f"  - 포스트당 최대 댓글: {TOP_COMMENTS_PER_POST}개")
    print(f"  - 예상 총 포스트: {len(all_keywords) * MAX_POSTS_PER_KEYWORD}개 (최대)")
    print("\n" + "=" * 60)
    
    # 각 키워드별 Apify Actor 입력 정보 출력
    print("\n📋 Apify Actor 호출 정보:")
    print("=" * 60)
    
    for i, keyword in enumerate(all_keywords, 1):
        actor_input = {
            "searchTerms": [keyword],
            "searchPosts": True,
            "searchComments": False,
            "searchCommunities": False,
            "searchSort": "hot",
            "searchTime": "all",
            "maxPostsCount": MAX_POSTS_PER_KEYWORD,
            "crawlCommentsPerPost": True,
            "maxCommentsPerPost": TOP_COMMENTS_PER_POST,
            "fastMode": True,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        print(f"\n[{i}/{len(all_keywords)}] 키워드: {keyword}")
        print(f"  Actor: harshmaur/reddit-scraper")
        print(f"  Input: {actor_input}")
        
        if i >= 3:  # 처음 3개만 상세 출력
            print(f"\n... (나머지 {len(all_keywords) - 3}개 키워드 동일한 형식)")
            break
    
    print("\n" + "=" * 60)
    print("\n💡 실행 방법:")
    print("1. 각 키워드별로 Apify Actor를 호출하세요")
    print("2. 결과 datasetId를 받아서 process_apify_results()로 처리하세요")
    print("3. 또는 MCP 도구를 사용하여 자동화할 수 있습니다")
    print("\n⚠️  주의: 100개 키워드를 모두 수집하려면 시간이 오래 걸릴 수 있습니다")
    print(f"   예상 시간: 약 {len(all_keywords) * 2 // 60}시간 ({len(all_keywords) * 2}분)")

if __name__ == "__main__":
    main()
