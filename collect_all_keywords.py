#!/usr/bin/env python3
"""
모든 키워드에 대해 Reddit 데이터 수집 및 데이터베이스 저장
MCP를 통해 Apify Actor 호출 및 결과 처리
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS, MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST
from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("collect_all_keywords")

def collect_all_keywords():
    """모든 키워드에 대해 데이터 수집"""
    # 파이프라인 run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run started: run_id={run_id}")
    
    total_stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }
    
    # 모든 키워드 수집
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        for keyword in keywords:
            all_keywords.append((category, keyword))
    
    logger.info(f"Total keywords to process: {len(all_keywords)}")
    
    # 각 키워드에 대해 Actor 호출 및 결과 처리
    # Note: 실제 Actor 호출은 MCP를 통해 수행되므로, 여기서는 키워드 목록과 설정만 출력
    # 실제 수집은 별도 스크립트나 MCP 도구를 통해 수행해야 함
    
    print("\n" + "="*80)
    print("키워드별 수집 설정 정보")
    print("="*80)
    
    for idx, (category, keyword) in enumerate(all_keywords, 1):
        print(f"\n[{idx}/{len(all_keywords)}] {category}: {keyword}")
        print(f"  Actor: harshmaur/reddit-scraper")
        print(f"  Input:")
        print(f"    searchTerms: ['{keyword}']")
        print(f"    maxPostsCount: {min(MAX_POSTS_PER_KEYWORD, 900)}")
        print(f"    maxCommentsPerPost: {TOP_COMMENTS_PER_POST}")
        print(f"    fastMode: true")
        print(f"    searchSort: 'hot'")
        print(f"    searchTime: 'all'")
    
    print("\n" + "="*80)
    print("수집 완료 후 각 키워드의 datasetId를 사용하여 데이터베이스에 저장하세요.")
    print("="*80)
    
    # 파이프라인 run 업데이트
    update_pipeline_run(run_id, "completed", metadata=total_stats)
    logger.info(f"Pipeline run completed: run_id={run_id}")

if __name__ == "__main__":
    collect_all_keywords()
