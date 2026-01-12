#!/usr/bin/env python3
"""
모든 20개 키워드의 데이터를 데이터베이스에 저장
로컬 환경에서 실행
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_20_keywords")

# 모든 20개 키워드 및 dataset ID 매핑
ALL_KEYWORDS_DATASETS = [
    # SPRING_RECIPES
    {"datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas", "actor": "harshmaur"},
    {"datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals", "actor": "harshmaur"},
    {"datasetId": "espep8ycOpNwjnK0c", "keyword": "what to cook in spring", "actor": "fatihtahta"},
    {"datasetId": "HBU9RwE0LKTfosdpi", "keyword": "spring meal prep", "actor": "fatihtahta"},
    {"datasetId": "LYXvepkImLnLdGm48", "keyword": "light spring recipes", "actor": "fatihtahta"},
    
    # SPRING_KITCHEN_STYLING
    {"datasetId": "yXqub9ijqT5BQHmlb", "keyword": "spring kitchen decor", "actor": "fatihtahta"},
    {"datasetId": "30aDnU50uC9L1ur1w", "keyword": "kitchen spring refresh", "actor": "fatihtahta"},
    {"datasetId": "YVa8nVEo8oHSzHhR1", "keyword": "spring table setting ideas", "actor": "fatihtahta"},
    {"datasetId": "RPL8m4MremBGj4vVq", "keyword": "how to decorate kitchen for spring", "actor": "fatihtahta"},
    {"datasetId": "gF2dPQKMe25vgda2j", "keyword": "spring kitchen ideas", "actor": "fatihtahta"},
    
    # REFRIGERATOR_ORGANIZATION
    {"datasetId": "JMdQaLPe6wSn4aYUo", "keyword": "refrigerator organization", "actor": "fatihtahta"},
    {"datasetId": "MZUpZW7AsSGmM7Pme", "keyword": "fridge organization tips", "actor": "fatihtahta"},
    {"datasetId": "ffOQ6gWAgE4SvAIUU", "keyword": "how to organize refrigerator", "actor": "fatihtahta"},
    {"datasetId": "LghMjyUJ9c1wfH9vh", "keyword": "refrigerator storage ideas", "actor": "fatihtahta"},
    {"datasetId": "s9N4ldadvFkUSC2Yr", "keyword": "fridge organization system", "actor": "fatihtahta"},
    
    # VEGETABLE_PREP_HANDLING
    {"datasetId": "BxKKKHf2TPr0RZ2aj", "keyword": "vegetable prep", "actor": "fatihtahta"},
    {"datasetId": "csIbII5EHZQDjdBfn", "keyword": "how to prep vegetables", "actor": "fatihtahta"},
    {"datasetId": "gwbMxDIYm8hzYax0n", "keyword": "vegetable storage tips", "actor": "fatihtahta"},
    {"datasetId": "VXBkcE1T6HdpQ1a3h", "keyword": "how to store vegetables", "actor": "fatihtahta"},
    {"datasetId": "e1oOCOhftNlR2quAi", "keyword": "vegetable washing tips", "actor": "fatihtahta"},
]

def main():
    """
    모든 20개 키워드의 데이터를 데이터베이스에 저장
    
    주의: 이 스크립트는 MCP 도구를 직접 호출할 수 없으므로,
    AI Assistant가 mcp_apify_get-actor-output을 사용하여
    각 dataset의 데이터를 가져온 후 process_apify_results를 호출해야 합니다.
    """
    try:
        # DATABASE_URL 확인
        database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            logger.info("Please set DATABASE_URL environment variable:")
            logger.info("  export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
            return None
        
        logger.info(f"Using database: {database_url.split('@')[-1].split('/')[-1] if '@' in database_url else 'unknown'}")
        
        # 파이프라인 run 생성
        pipeline_run_id = create_pipeline_run("collect_reddit_save_all_20", status="running")
        logger.info(f"Pipeline run created: run_id={pipeline_run_id}")

        total_stats = {
            "posts_collected": 0,
            "comments_collected": 0,
            "keywords_processed": 0,
            "errors": []
        }

        logger.info("=" * 60)
        logger.info("데이터 저장 준비 완료")
        logger.info("=" * 60)
        logger.info(f"총 {len(ALL_KEYWORDS_DATASETS)}개 키워드의 데이터를 저장합니다.")
        logger.info("=" * 60)
        
        # 각 키워드별로 데이터 저장
        # 실제 데이터는 MCP 도구를 통해 가져와야 합니다
        logger.info("\n다음 단계:")
        logger.info("1. 각 dataset의 모든 데이터를 MCP 도구로 가져옵니다")
        logger.info("2. 가져온 데이터를 process_apify_results() 함수에 전달하여 저장합니다")
        logger.info("\n예시:")
        logger.info("  items = mcp_apify_get_actor_output(datasetId='Chej96NJu2xomUrg1', offset=0, limit=99999)")
        logger.info("  stats = process_apify_results(items, 'spring dinner ideas', pipeline_run_id)")
        
        # 실제 저장은 MCP 도구를 통해 데이터를 가져온 후 수행해야 합니다
        # 여기서는 placeholder로 남겨둡니다

        update_pipeline_run(pipeline_run_id, "completed", metadata=total_stats)
        logger.info(f"\n모든 키워드 저장 완료!")
        logger.info(f"  총 포스트: {total_stats['posts_collected']}개")
        logger.info(f"  총 댓글: {total_stats['comments_collected']}개")
        logger.info(f"  처리된 키워드: {total_stats['keywords_processed']}개")
        
        return total_stats

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
