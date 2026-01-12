#!/usr/bin/env python3
"""
나머지 키워드 수집 계속 진행
MCP를 통해 Apify Actor 호출
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import REDDIT_KEYWORDS
from worker.pipeline.logging import setup_logger

logger = setup_logger("continue_collection")

# 이미 수집 완료된 키워드
COLLECTED = [
    "spring dinner ideas",
    "easy spring meals"
]

def get_remaining_keywords():
    """수집하지 않은 키워드 목록 반환"""
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        for keyword in keywords:
            all_keywords.append((category, keyword))
    
    remaining = [(cat, kw) for cat, kw in all_keywords if kw not in COLLECTED]
    return remaining

def main():
    """메인 함수"""
    remaining = get_remaining_keywords()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"남은 키워드 수집: {len(remaining)}개")
    logger.info(f"{'='*80}\n")
    
    # 각 키워드에 대한 Actor 호출 정보 출력
    for idx, (category, keyword) in enumerate(remaining, 1):
        logger.info(f"[{idx}/{len(remaining)}] {category}: {keyword}")
        logger.info(f"  Actor: harshmaur/reddit-scraper")
        logger.info(f"  Input:")
        logger.info(f"    searchTerms: ['{keyword}']")
        logger.info(f"    maxPostsCount: 900")
        logger.info(f"    maxCommentsPerPost: 3")
        logger.info(f"    fastMode: true")
        logger.info(f"    searchSort: 'hot'")
        logger.info(f"    searchTime: 'all'")
        logger.info(f"")
        logger.info(f"  💡 MCP 호출:")
        logger.info(f"    mcp_apify_call-actor(")
        logger.info(f"      actor='harshmaur/reddit-scraper',")
        logger.info(f"      step='call',")
        logger.info(f"      input={{'searchTerms': ['{keyword}'], ...}}")
        logger.info(f"    )")
        logger.info(f"")

if __name__ == "__main__":
    main()
