#!/usr/bin/env python3
"""
모든 20개 키워드의 Apify 데이터셋을 데이터베이스에 저장하는 스크립트 (Apify API 직접 사용)

사용법:
    export APIFY_API_TOKEN="your-apify-token"
    export DATABASE_URL="postgresql://..."
    python save_all_keywords_api.py
"""
import os
import sys
from pathlib import Path
from apify_client import ApifyClient

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_keywords_api")

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

def fetch_dataset_items(apify_client: ApifyClient, dataset_id: str, limit: int = None, offset: int = 0):
    """
    Apify API를 사용하여 데이터셋 아이템 가져오기
    
    Args:
        apify_client: ApifyClient 인스턴스
        dataset_id: Apify dataset ID
        limit: 가져올 최대 아이템 수 (None이면 모두 가져옴)
        offset: 시작 오프셋
    
    Returns:
        아이템 리스트
    """
    items = []
    current_offset = offset
    
    while True:
        # 한 번에 최대 1000개씩 가져오기
        batch_limit = min(1000, limit - len(items)) if limit else 1000
        
        try:
            dataset_items = apify_client.dataset(dataset_id).list_items(
                limit=batch_limit,
                offset=current_offset,
                clean=True  # 빈 필드 제거
            )
            
            batch_items = list(dataset_items.get('items', []))
            
            if not batch_items:
                break
            
            items.extend(batch_items)
            logger.info(f"  Fetched {len(batch_items)} items (total: {len(items)})")
            
            # limit에 도달했거나 더 이상 아이템이 없으면 종료
            if limit and len(items) >= limit:
                break
            
            if len(batch_items) < batch_limit:
                break
            
            current_offset += batch_limit
            
        except Exception as e:
            logger.error(f"  Error fetching items: {e}")
            break
    
    return items

def save_dataset(apify_client: ApifyClient, dataset_id: str, keyword: str, run_id: int):
    """
    데이터셋 아이템을 가져와서 데이터베이스에 저장
    
    Args:
        apify_client: ApifyClient 인스턴스
        dataset_id: Apify dataset ID
        keyword: 키워드
        run_id: Pipeline run ID
    
    Returns:
        통계 딕셔너리
    """
    logger.info(f"Fetching dataset: {dataset_id} for keyword: {keyword}")
    
    try:
        # 데이터셋 메타데이터 확인
        dataset_info = apify_client.dataset(dataset_id).get()
        item_count = dataset_info.get('itemCount', 0)
        logger.info(f"  Dataset has {item_count} items")
        
        # 모든 아이템 가져오기
        items = fetch_dataset_items(apify_client, dataset_id)
        
        if not items:
            logger.warning(f"  ⚠️  No items found in dataset {dataset_id}")
            return {"posts_collected": 0, "comments_collected": 0, "errors": []}
        
        # 데이터베이스에 저장
        logger.info(f"  Processing {len(items)} items...")
        stats = process_apify_results(items, keyword, run_id)
        
        logger.info(f"  ✅ {keyword}: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
        return stats
        
    except Exception as e:
        logger.error(f"  ❌ Error processing {keyword}: {e}", exc_info=True)
        return {"posts_collected": 0, "comments_collected": 0, "errors": [str(e)]}

def main():
    """메인 함수"""
    # APIFY_API_TOKEN 확인 (APIFY_TOKEN도 지원)
    apify_token = os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_TOKEN")
    if not apify_token:
        logger.error("❌ APIFY_API_TOKEN 또는 APIFY_TOKEN이 설정되지 않았습니다.")
        logger.error("   Apify 콘솔(https://console.apify.com/)에서 API Token을 확인하세요:")
        logger.error("   Settings > Integrations > API tokens")
        logger.error("   export APIFY_API_TOKEN='your-token-here' 또는 APIFY_TOKEN='your-token-here'")
        sys.exit(1)
    
    # DATABASE_URL 확인 (여러 환경 변수 이름 지원)
    db_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    if not db_url:
        logger.error("❌ DATABASE_URL이 설정되지 않았습니다.")
        logger.error("   Railway DATABASE_URL 설정 방법:")
        logger.error("   1. Railway 대시보드 접속: https://railway.app/")
        logger.error("   2. 프로젝트 선택 > PostgreSQL 서비스 클릭 (서비스 이름: 'Postgres-tezK' 또는 'Postgres')")
        logger.error("   3. 'Variables' 탭에서 DATABASE_URL 복사")
        logger.error("   4. export DATABASE_URL='postgresql://...'")
        logger.error("   또는 Railway Worker 서비스의 'Variables' 탭에서 직접 설정 (자동 주입)")
        sys.exit(1)
    
    # 데이터베이스 연결 확인
    if not check_database_connection():
        sys.exit(1)
    
    # Apify 클라이언트 초기화
    apify_client = ApifyClient(apify_token)
    logger.info("✅ Apify 클라이언트 초기화 완료")
    
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
        
        try:
            stats = save_dataset(apify_client, dataset_id, keyword, run_id)
            
            total_stats["keywords_processed"] += 1
            total_stats["total_posts"] += stats["posts_collected"]
            total_stats["total_comments"] += stats["comments_collected"]
            if stats.get("errors"):
                total_stats["errors"].extend(stats["errors"])
                
        except Exception as e:
            logger.error(f"  ❌ Fatal error processing {keyword}: {e}", exc_info=True)
            total_stats["errors"].append(f"{keyword}: {str(e)}")
    
    # Pipeline run 업데이트
    update_pipeline_run(run_id, "completed", metadata=total_stats)
    
    logger.info(f"\n{'='*60}")
    logger.info("저장 완료!")
    logger.info(f"  처리된 키워드: {total_stats['keywords_processed']}/{len(COLLECTED_DATASETS)}")
    logger.info(f"  총 포스트: {total_stats['total_posts']}")
    logger.info(f"  총 댓글: {total_stats['total_comments']}")
    if total_stats["errors"]:
        logger.warning(f"  오류: {len(total_stats['errors'])}개")
    logger.info(f"{'='*60}\n")

if __name__ == "__main__":
    main()
