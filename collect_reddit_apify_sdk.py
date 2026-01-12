#!/usr/bin/env python3
"""
Reddit 데이터 본격 수집 - Apify Python SDK 사용
각 키워드별로 Apify Actor를 호출하고 결과를 데이터베이스에 저장
"""
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from apify_client import ApifyClient
except ImportError:
    print("⚠️  Apify Python SDK가 설치되지 않았습니다.")
    print("설치: pip install apify-client")
    sys.exit(1)

from worker.pipeline.config import REDDIT_KEYWORDS, MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST
from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("collect_reddit_apify_sdk")

def collect_keyword_with_apify(keyword: str, run_id: int, apify_client: ApifyClient) -> Dict[str, Any]:
    """
    Apify SDK를 사용하여 키워드별 Reddit 데이터 수집
    
    Args:
        keyword: 검색 키워드
        run_id: Pipeline run ID
        apify_client: ApifyClient 인스턴스
    
    Returns:
        수집 통계
    """
    logger.info(f"Collecting Reddit data for keyword: {keyword}")
    
    # Actor 입력 구성
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
    
    try:
        # Actor 실행
        logger.info(f"  → Starting Apify Actor run for '{keyword}'...")
        run = apify_client.actor("harshmaur/reddit-scraper").call(run_input=actor_input)
        
        # 실행 완료 대기
        logger.info(f"  → Waiting for Actor run to complete...")
        apify_client.run(run["defaultDatasetId"]).wait_for_finish()
        
        # 결과 가져오기
        logger.info(f"  → Fetching results from dataset...")
        dataset_items = apify_client.dataset(run["defaultDatasetId"]).list_items()
        
        items = [item for item in dataset_items.items]
        logger.info(f"  → Received {len(items)} items")
        
        # 데이터베이스에 저장
        if items:
            stats = process_apify_results(items, keyword, run_id)
            logger.info(f"  → Saved: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
            return stats
        else:
            logger.warning(f"  → No items returned for keyword '{keyword}'")
            return {"posts_collected": 0, "comments_collected": 0, "errors": []}
            
    except Exception as e:
        logger.error(f"Error collecting data for keyword '{keyword}': {e}")
        return {"posts_collected": 0, "comments_collected": 0, "errors": [str(e)]}

def main():
    """메인 실행 함수"""
    # DATABASE_URL 확인
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        print("\n환경 변수 설정:")
        print("export DATABASE_URL='postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway'")
        sys.exit(1)
    
    # Apify API Token 확인
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        logger.error("APIFY_TOKEN 환경 변수가 설정되지 않았습니다.")
        print("\nApify API Token 설정:")
        print("1. https://console.apify.com/account/integrations 에서 API Token 확인")
        print("2. export APIFY_TOKEN='your-apify-token'")
        sys.exit(1)
    
    # Apify Client 초기화
    apify_client = ApifyClient(apify_token)
    
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
    print(f"  - 예상 시간: 약 {len(all_keywords) * 2 // 60}시간 ({len(all_keywords) * 2}분)")
    print("\n" + "=" * 60)
    
    total_posts = 0
    total_comments = 0
    processed = 0
    errors = []
    
    # 각 키워드별로 수집
    for i, keyword in enumerate(all_keywords, 1):
        try:
            print(f"\n[{i}/{len(all_keywords)}] 키워드: {keyword}")
            
            # Apify를 통해 수집
            stats = collect_keyword_with_apify(keyword, run_id, apify_client)
            
            total_posts += stats.get("posts_collected", 0)
            total_comments += stats.get("comments_collected", 0)
            processed += 1
            
            if stats.get("errors"):
                errors.extend([f"{keyword}: {e}" for e in stats["errors"]])
            
            print(f"  ✅ 완료: {stats.get('posts_collected', 0)} 포스트, {stats.get('comments_collected', 0)} 댓글")
            
            # 진행 상황 업데이트
            if i % 10 == 0:
                update_pipeline_run(run_id, status="running", metadata={
                    "keywords_processed": processed,
                    "total_keywords": len(all_keywords),
                    "total_posts": total_posts,
                    "total_comments": total_comments,
                    "progress": f"{i}/{len(all_keywords)}"
                })
                print(f"\n📊 진행 상황: {i}/{len(all_keywords)} ({i*100//len(all_keywords)}%)")
                print(f"   누적 포스트: {total_posts}개, 댓글: {total_comments}개")
            
            # Rate limiting
            if i < len(all_keywords):
                time.sleep(2)  # 각 키워드 사이 2초 대기
                
        except KeyboardInterrupt:
            logger.warning("수집이 중단되었습니다.")
            print(f"\n⚠️  수집 중단됨: {processed}/{len(all_keywords)} 키워드 처리 완료")
            break
        except Exception as e:
            logger.error(f"Error processing keyword '{keyword}': {e}")
            errors.append(f"{keyword}: {str(e)}")
            print(f"  ❌ 에러: {e}")
    
    # Pipeline run 완료 업데이트
    update_pipeline_run(run_id, status="completed", metadata={
        "keywords_processed": processed,
        "total_keywords": len(all_keywords),
        "total_posts": total_posts,
        "total_comments": total_comments,
        "errors": errors
    })
    
    print("\n" + "=" * 60)
    print(f"\n✅ Reddit 수집 완료!")
    print(f"  - 처리된 키워드: {processed}/{len(all_keywords)}")
    print(f"  - 총 포스트: {total_posts}개")
    print(f"  - 총 댓글: {total_comments}개")
    
    if errors:
        print(f"\n⚠️  에러 발생: {len(errors)}개")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... 외 {len(errors) - 10}개 에러")

if __name__ == "__main__":
    main()
