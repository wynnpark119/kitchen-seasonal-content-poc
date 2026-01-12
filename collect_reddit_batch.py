#!/usr/bin/env python3
"""
Reddit 데이터 본격 수집 스크립트
Apify Actor를 사용하여 키워드별로 Reddit 포스트 수집
"""
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS, MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST
from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("collect_reddit_batch")

def collect_keyword_via_apify(keyword: str, run_id: int):
    """
    Apify Actor를 사용하여 키워드별 Reddit 데이터 수집
    
    Note: 실제 Apify 호출은 MCP 도구를 사용하거나
    Apify Python SDK를 사용해야 합니다.
    """
    logger.info(f"Collecting Reddit data for keyword: {keyword}")
    
    # Apify Actor 입력 구성
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
    
    logger.info(f"Actor input prepared for '{keyword}': maxPosts={MAX_POSTS_PER_KEYWORD}, maxCommentsPerPost={TOP_COMMENTS_PER_POST}")
    logger.info("Note: Actual Apify Actor call should be made via MCP or Apify SDK")
    
    return actor_input

def main():
    """메인 실행 함수"""
    # DATABASE_URL 확인
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # Pipeline run 생성
    run_id = create_pipeline_run("collect", status="running")
    logger.info(f"Pipeline run started: run_id={run_id}")
    
    # 모든 키워드 수집
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        all_keywords.extend(keywords)
    
    logger.info(f"Starting Reddit collection for {len(all_keywords)} keywords")
    logger.info("=" * 60)
    
    total_posts = 0
    total_comments = 0
    processed = 0
    errors = []
    
    # 각 키워드별로 수집 (실제로는 Apify Actor 호출 필요)
    for i, keyword in enumerate(all_keywords, 1):
        try:
            logger.info(f"[{i}/{len(all_keywords)}] Processing keyword: {keyword}")
            
            # Apify Actor 입력 준비
            actor_input = collect_keyword_via_apify(keyword, run_id)
            
            logger.info(f"  → Actor input ready. Call Apify Actor with this input.")
            logger.info(f"  → After Actor completes, use process_apify_results() to save data")
            
            # 실제 수집은 Apify Actor 호출 후 결과를 받아서 처리
            # 여기서는 로그만 남기고, 실제 호출은 별도로 수행
            
            processed += 1
            
            # Rate limiting
            if i < len(all_keywords):
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error processing keyword '{keyword}': {e}")
            errors.append(f"{keyword}: {str(e)}")
    
    # Pipeline run 업데이트
    update_pipeline_run(run_id, status="completed", metadata={
        "keywords_processed": processed,
        "total_keywords": len(all_keywords),
        "errors": errors
    })
    
    logger.info("=" * 60)
    logger.info(f"Reddit collection preparation completed")
    logger.info(f"  Keywords processed: {processed}/{len(all_keywords)}")
    logger.info(f"  Errors: {len(errors)}")
    
    if errors:
        logger.warning("Errors occurred:")
        for error in errors[:10]:  # 처음 10개만 표시
            logger.warning(f"  - {error}")

if __name__ == "__main__":
    main()
