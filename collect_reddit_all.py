#!/usr/bin/env python3
"""
Reddit 데이터 본격 수집 - Apify Actor 호출 및 결과 처리
각 키워드별로 Apify Actor를 호출하고 결과를 데이터베이스에 저장
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS, MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST
from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("collect_reddit_all")

def collect_keyword(keyword: str, run_id: int, actor_results: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    키워드별 Reddit 데이터 수집 및 저장
    
    Args:
        keyword: 검색 키워드
        run_id: Pipeline run ID
        actor_results: Apify Actor 결과 (datasetId 또는 items)
    
    Returns:
        수집 통계
    """
    logger.info(f"Processing keyword: {keyword}")
    
    if actor_results:
        # Actor 결과가 제공된 경우 처리
        if 'datasetId' in actor_results:
            logger.info(f"  → Dataset ID: {actor_results['datasetId']}")
            logger.info(f"  → Use mcp_apify_get-actor-output to fetch items")
            # 실제로는 get-actor-output으로 items를 가져와야 함
            return {"status": "pending", "datasetId": actor_results['datasetId']}
        elif 'items' in actor_results:
            # Items가 직접 제공된 경우 처리
            items = actor_results['items']
            logger.info(f"  → Processing {len(items)} items")
            stats = process_apify_results(items, keyword, run_id)
            logger.info(f"  → Saved: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
            return stats
    
    # Actor 호출 필요
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
    
    logger.info(f"  → Actor input ready: {json.dumps(actor_input, indent=2)}")
    return {"status": "ready_for_actor_call", "input": actor_input}

def main():
    """메인 실행 함수"""
    # DATABASE_URL 확인
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        print("\n환경 변수 설정:")
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
    print(f"\n📊 수집 시작:")
    print(f"  - 총 키워드: {len(all_keywords)}개")
    print(f"  - 각 키워드당 최대 포스트: {MAX_POSTS_PER_KEYWORD}개")
    print(f"  - 포스트당 최대 댓글: {TOP_COMMENTS_PER_POST}개")
    print("\n" + "=" * 60)
    
    total_posts = 0
    total_comments = 0
    processed = 0
    errors = []
    
    # 각 키워드별로 처리
    for i, keyword in enumerate(all_keywords, 1):
        try:
            print(f"\n[{i}/{len(all_keywords)}] 키워드: {keyword}")
            
            # 키워드 처리 (Actor 호출 필요)
            result = collect_keyword(keyword, run_id)
            
            if result.get("status") == "ready_for_actor_call":
                print(f"  ⏳ Apify Actor 호출 필요")
                print(f"  → Actor: harshmaur/reddit-scraper")
                print(f"  → Input: {json.dumps(result['input'], indent=4)}")
            
            processed += 1
            
            # Rate limiting
            if i < len(all_keywords):
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error processing keyword '{keyword}': {e}")
            errors.append(f"{keyword}: {str(e)}")
            print(f"  ❌ 에러: {e}")
    
    # Pipeline run 업데이트
    update_pipeline_run(run_id, status="running", metadata={
        "keywords_processed": processed,
        "total_keywords": len(all_keywords),
        "total_posts": total_posts,
        "total_comments": total_comments,
        "errors": errors
    })
    
    print("\n" + "=" * 60)
    print(f"\n✅ 키워드 처리 준비 완료: {processed}/{len(all_keywords)}")
    print(f"📝 총 포스트: {total_posts}개")
    print(f"💬 총 댓글: {total_comments}개")
    
    if errors:
        print(f"\n⚠️  에러 발생: {len(errors)}개")
        for error in errors[:5]:
            print(f"  - {error}")

if __name__ == "__main__":
    main()
