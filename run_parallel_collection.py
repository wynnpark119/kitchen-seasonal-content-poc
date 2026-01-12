#!/usr/bin/env python3
"""
Railway Worker에서 실행할 병렬 Reddit 수집 스크립트
Apify Client SDK를 사용하여 20개 키워드를 병렬로 수집
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.collect_reddit_parallel import collect_reddit_data_parallel
from worker.pipeline.logging import setup_logger

logger = setup_logger("run_parallel_collection")

def main():
    """메인 함수"""
    # 환경 변수 확인
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        logger.error("APIFY_API_TOKEN 환경 변수가 설정되지 않았습니다.")
        logger.error("Railway 환경 변수에 APIFY_API_TOKEN을 설정하세요.")
        return
    
    database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        logger.error("Railway 환경 변수에 DATABASE_URL을 설정하세요.")
        return
    
    # Pipeline run 생성
    run_id = create_pipeline_run("collect_parallel", "running")
    logger.info(f"Pipeline run created: run_id={run_id}")
    
    try:
        # 병렬 수집 실행
        stats = collect_reddit_data_parallel(run_id, dry_run=False)
        
        # Pipeline run 업데이트
        update_pipeline_run(run_id, "completed", metadata=stats)
        
        logger.info("=" * 60)
        logger.info("병렬 수집 완료!")
        logger.info("=" * 60)
        logger.info(f"수집된 포스트: {stats['posts_collected']}개")
        logger.info(f"수집된 댓글: {stats['comments_collected']}개")
        logger.info(f"처리된 키워드: {stats['keywords_processed']}개")
        logger.info(f"시작된 Run: {stats['runs_started']}개")
        logger.info(f"완료된 Run: {stats['runs_completed']}개")
        
        if stats["errors"]:
            logger.warning(f"오류 발생: {len(stats['errors'])}개")
            for error in stats["errors"]:
                logger.warning(f"  - {error}")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        update_pipeline_run(run_id, "failed", error_message=str(e))
        raise

if __name__ == "__main__":
    main()
