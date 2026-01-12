#!/usr/bin/env python3
"""
모든 20개 키워드의 Apify 데이터셋을 데이터베이스에 저장하는 스크립트

사용법:
    export DATABASE_URL="postgresql://..."
    python save_all_keywords_to_db.py
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_keywords")

# 모든 키워드-데이터셋 매핑
COLLECTED_DATASETS = [
    # SPRING_RECIPES
    {"keyword": "spring dinner ideas", "dataset_id": "Chej96NJu2xomUrg1"},
    {"keyword": "easy spring meals", "dataset_id": "hYNaDehMRGFbLd9sW"},
    {"keyword": "what to cook in spring", "dataset_id": "espep8ycOpNwjnK0c"},
    {"keyword": "spring meal prep", "dataset_id": "HBU9RwE0LKTfosdpi"},
    {"keyword": "light spring recipes", "dataset_id": "LYXvepkImLnLdGm48"},
    # SPRING_KITCHEN_STYLING
    {"keyword": "spring kitchen decor", "dataset_id": "yXqub9ijqT5BQHmlb"},
    {"keyword": "kitchen spring refresh", "dataset_id": "30aDnU50uC9L1ur1w"},
    {"keyword": "spring table setting ideas", "dataset_id": "YVa8nVEo8oHSzHhR1"},
    {"keyword": "how to decorate kitchen for spring", "dataset_id": "RPL8m4MremBGj4vVq"},
    {"keyword": "spring kitchen ideas", "dataset_id": "gF2dPQKMe25vgda2j"},
    # REFRIGERATOR_ORGANIZATION
    {"keyword": "refrigerator organization", "dataset_id": "JMdQaLPe6wSn4aYUo"},
    {"keyword": "fridge organization tips", "dataset_id": "MZUpZW7AsSGmM7Pme"},
    {"keyword": "how to organize refrigerator", "dataset_id": "ffOQ6gWAgE4SvAIUU"},
    {"keyword": "refrigerator storage ideas", "dataset_id": "LghMjyUJ9c1wfH9vh"},
    {"keyword": "fridge organization system", "dataset_id": "s9N4ldadvFkUSC2Yr"},
    # VEGETABLE_PREP_HANDLING
    {"keyword": "vegetable prep", "dataset_id": "BxKKKHf2TPr0RZ2aj"},
    {"keyword": "how to prep vegetables", "dataset_id": "csIbII5EHZQDjdBfn"},
    {"keyword": "vegetable storage tips", "dataset_id": "gwbMxDIYm8hzYax0n"},
    {"keyword": "how to store vegetables", "dataset_id": "VXBkcE1T6HdpQ1a3h"},
    {"keyword": "vegetable washing tips", "dataset_id": "e1oOCOhftNlR2quAi"},
]

def check_database_connection():
    """데이터베이스 연결 확인"""
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("✅ 데이터베이스 연결 성공")
        return True
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        return False

def save_dataset(dataset_id: str, keyword: str, run_id: int, items: list):
    """
    데이터셋 아이템을 데이터베이스에 저장
    
    Args:
        dataset_id: Apify dataset ID
        keyword: 키워드
        run_id: Pipeline run ID
        items: 데이터셋 아이템 리스트
    """
    logger.info(f"Processing {len(items)} items for keyword: {keyword}")
    
    try:
        stats = process_apify_results(items, keyword, run_id)
        logger.info(f"✅ {keyword}: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
        return stats
    except Exception as e:
        logger.error(f"❌ Error processing {keyword}: {e}", exc_info=True)
        return {"posts_collected": 0, "comments_collected": 0, "errors": [str(e)]}

def main():
    """메인 함수"""
    # DATABASE_URL 확인
    db_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL이 설정되지 않았습니다.")
        logger.error("   Railway DATABASE_URL을 설정해주세요:")
        logger.error("   export DATABASE_URL='postgresql://...'")
        sys.exit(1)
    
    # 데이터베이스 연결 확인
    if not check_database_connection():
        sys.exit(1)
    
    # Pipeline run 생성
    run_id = create_pipeline_run("collect", status="running")
    logger.info(f"Pipeline run 생성: run_id={run_id}")
    
    total_stats = {
        "keywords_processed": 0,
        "total_posts": 0,
        "total_comments": 0,
        "errors": []
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"총 {len(COLLECTED_DATASETS)}개 키워드 데이터 저장 시작")
    logger.info(f"{'='*60}\n")
    
    # 각 키워드 처리
    for idx, dataset_info in enumerate(COLLECTED_DATASETS, 1):
        keyword = dataset_info["keyword"]
        dataset_id = dataset_info["dataset_id"]
        
        logger.info(f"\n[{idx}/{len(COLLECTED_DATASETS)}] Processing: {keyword}")
        logger.info(f"  Dataset ID: {dataset_id}")
        
        # 이 스크립트는 MCP 호출을 직접 하지 않음
        # MCP 호출은 AI assistant가 mcp_apify_get-actor-output으로 수행
        # 여기서는 items를 파라미터로 받아서 처리하는 구조
        logger.warning(f"  ⚠️  MCP 호출 필요: mcp_apify_get-actor-output(datasetId='{dataset_id}')")
    
    logger.info(f"\n{'='*60}")
    logger.info("스크립트 준비 완료")
    logger.info("MCP를 통해 데이터를 가져온 후 이 스크립트를 수정하여 실행하거나,")
    logger.info("AI assistant가 직접 MCP 호출을 수행해야 합니다.")
    logger.info(f"{'='*60}\n")
    
    # Pipeline run 업데이트
    update_pipeline_run(run_id, "completed", metadata=total_stats)
    logger.info(f"Pipeline run 완료: run_id={run_id}")

if __name__ == "__main__":
    main()
