#!/usr/bin/env python3
"""
수집 완료된 데이터 저장 및 나머지 키워드 수집 계속 진행
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.config import REDDIT_KEYWORDS
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_and_continue")

# 수집 완료된 키워드 정보
COLLECTED_KEYWORDS = [
    {
        "keyword": "spring dinner ideas",
        "datasetId": "Yu6o5q1FKWhb4jdcH",
        "total_items": 889,
        "status": "collected"
    },
    {
        "keyword": "easy spring meals",
        "datasetId": "BdiwpZTKHdd7SATso",
        "total_items": 830,
        "status": "collected"
    }
]

def get_all_keywords():
    """모든 키워드 목록 반환"""
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        for keyword in keywords:
            all_keywords.append({
                "category": category,
                "keyword": keyword
            })
    return all_keywords

def get_remaining_keywords():
    """아직 수집하지 않은 키워드 목록 반환"""
    all_keywords = get_all_keywords()
    collected_keyword_list = [kw["keyword"] for kw in COLLECTED_KEYWORDS]
    
    remaining = []
    for kw in all_keywords:
        if kw["keyword"] not in collected_keyword_list:
            remaining.append(kw)
    
    return remaining

def main():
    """메인 함수"""
    # 파이프라인 run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    # 수집 완료된 키워드 정보 출력
    logger.info(f"\n{'='*80}")
    logger.info("수집 완료된 키워드 (데이터베이스 저장 필요):")
    logger.info(f"{'='*80}")
    for kw in COLLECTED_KEYWORDS:
        logger.info(f"  - {kw['keyword']}")
        logger.info(f"    Dataset ID: {kw['datasetId']}")
        logger.info(f"    Total items: {kw['total_items']}")
        logger.info(f"    저장 방법: mcp_apify_get-actor-output으로 데이터 가져온 후")
        logger.info(f"              process_apify_results(items, '{kw['keyword']}', {run_id}) 호출")
    
    # 남은 키워드 정보
    remaining = get_remaining_keywords()
    logger.info(f"\n{'='*80}")
    logger.info(f"남은 키워드 수집 필요: {len(remaining)}개")
    logger.info(f"{'='*80}")
    
    # 카테고리별로 그룹화하여 출력
    by_category = {}
    for kw in remaining:
        cat = kw["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(kw["keyword"])
    
    for category, keywords in by_category.items():
        logger.info(f"\n{category} ({len(keywords)}개):")
        for keyword in keywords:
            logger.info(f"  - {keyword}")
            logger.info(f"    Actor 호출 필요:")
            logger.info(f"      searchTerms: ['{keyword}']")
            logger.info(f"      maxPostsCount: 900")
            logger.info(f"      maxCommentsPerPost: 3")
    
    # 파이프라인 run 업데이트
    update_pipeline_run(run_id, "running", metadata={
        "collected": len(COLLECTED_KEYWORDS),
        "remaining": len(remaining),
        "collected_keywords": COLLECTED_KEYWORDS
    })
    
    logger.info(f"\n{'='*80}")
    logger.info("다음 단계:")
    logger.info("1. 수집 완료된 키워드 데이터를 mcp_apify_get-actor-output으로 가져오기")
    logger.info("2. process_apify_results()로 데이터베이스에 저장")
    logger.info("3. 나머지 키워드에 대해 mcp_apify_call-actor로 계속 수집")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    main()
