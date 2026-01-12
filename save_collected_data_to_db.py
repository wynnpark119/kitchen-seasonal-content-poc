#!/usr/bin/env python3
"""
수집 완료된 Reddit 데이터를 데이터베이스에 저장
MCP를 통해 데이터를 가져와서 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_collected_data")

# 수집 완료된 키워드 정보
COLLECTED_KEYWORDS = [
    {
        "keyword": "spring dinner ideas",
        "datasetId": "Yu6o5q1FKWhb4jdcH",
        "total_items": 889
    },
    {
        "keyword": "easy spring meals",
        "datasetId": "BdiwpZTKHdd7SATso",
        "total_items": 830
    }
]

def save_keyword_data(items, keyword, run_id):
    """키워드 데이터를 데이터베이스에 저장"""
    try:
        logger.info(f"Processing {len(items)} items for keyword: {keyword}")
        stats = process_apify_results(items, keyword, run_id)
        logger.info(f"✅ Saved: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
        if stats.get('errors'):
            logger.warning(f"⚠️  Errors: {len(stats['errors'])}")
        return stats
    except Exception as e:
        logger.error(f"❌ Error saving data for '{keyword}': {e}", exc_info=True)
        return {"posts_collected": 0, "comments_collected": 0, "errors": [str(e)]}

def main():
    """메인 함수 - MCP를 통해 데이터를 가져와서 저장"""
    # 환경 변수 확인
    if not os.getenv("DATABASE_URL"):
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        logger.info("Railway 환경에서는 자동으로 설정되거나, .env 파일에 설정하세요.")
        return
    
    # 파이프라인 run 생성
    run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    total_stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }
    
    logger.info(f"\n{'='*80}")
    logger.info(f"수집 완료된 {len(COLLECTED_KEYWORDS)}개 키워드 데이터 저장 시작")
    logger.info(f"{'='*80}\n")
    
    for idx, kw_info in enumerate(COLLECTED_KEYWORDS, 1):
        keyword = kw_info["keyword"]
        dataset_id = kw_info["datasetId"]
        total_items = kw_info["total_items"]
        
        logger.info(f"[{idx}/{len(COLLECTED_KEYWORDS)}] Processing: {keyword}")
        logger.info(f"  Dataset ID: {dataset_id}")
        logger.info(f"  Total items: {total_items}")
        
        # MCP를 통해 데이터 가져오기
        # Note: 실제 실행 시에는 mcp_apify_get-actor-output을 사용해야 함
        logger.info(f"  ⏳ Fetching data from Apify dataset...")
        logger.info(f"  💡 Use: mcp_apify_get-actor-output(datasetId='{dataset_id}', limit={total_items}, offset=0)")
        
        # 여기서는 실제 데이터를 가져올 수 없으므로, 사용자가 직접 MCP를 통해 가져와야 함
        logger.warning(f"  ⚠️  데이터를 가져오려면 MCP 도구를 사용하세요")
        logger.info(f"  📝 가져온 후: save_keyword_data(items, '{keyword}', {run_id}) 호출")
    
    logger.info(f"\n{'='*80}")
    logger.info("데이터 저장 완료 후 파이프라인 run을 업데이트하세요")
    logger.info(f"{'='*80}")
    
    # 파이프라인 run 업데이트
    update_pipeline_run(run_id, "running", metadata={
        "collected_keywords": COLLECTED_KEYWORDS,
        "status": "waiting_for_mcp_data_fetch"
    })

if __name__ == "__main__":
    main()
