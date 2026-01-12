#!/usr/bin/env python3
"""
로컬에서 Apify 데이터셋을 가져와서 JSON으로 저장하고 DB에 적재하는 스크립트
Apify Python SDK를 사용하여 API로 데이터를 가져옵니다.

사용법:
    export APIFY_API_TOKEN="your-apify-token"
    export DATABASE_URL="postgresql://..."
    python save_keywords_local.py
"""
import os
import sys
import json
from pathlib import Path
from apify_client import ApifyClient

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_keywords_local")

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
        from worker.pipeline.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
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

def download_dataset_to_json(apify_client: ApifyClient, dataset_id: str, keyword: str) -> Path:
    """
    Apify API를 사용하여 데이터셋을 가져와서 JSON 파일로 저장
    
    Args:
        apify_client: ApifyClient 인스턴스
        dataset_id: Apify dataset ID
        keyword: 키워드 (파일명에 사용)
    
    Returns:
        저장된 JSON 파일 경로
    """
    logger.info(f"📥 Apify API로 데이터셋 가져오기: {dataset_id} (키워드: {keyword})")
    
    try:
        # 데이터셋 메타데이터 확인
        dataset_info = apify_client.dataset(dataset_id).get()
        item_count = dataset_info.get('itemCount', 0)
        logger.info(f"  Dataset has {item_count} items")
        
        # 모든 아이템 가져오기
        items = fetch_dataset_items(apify_client, dataset_id)
        
        if not items:
            logger.warning(f"  ⚠️  No items found in dataset {dataset_id}")
            return None
        
        # JSON 파일로 저장
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        
        safe_keyword = keyword.replace(' ', '_').replace('/', '_')
        json_file = data_dir / f"{safe_keyword}_{dataset_id}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        logger.info(f"  ✅ {len(items)}개 아이템을 JSON 파일로 저장: {json_file}")
        return json_file
        
    except Exception as e:
        logger.error(f"  ❌ Error downloading dataset {dataset_id}: {e}", exc_info=True)
        return None

def save_dataset_from_json_file(json_file_path: str, keyword: str, run_id: int):
    """
    JSON 파일에서 데이터를 읽어서 DB에 저장
    """
    logger.info(f"📂 JSON 파일에서 읽기: {json_file_path}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        if not isinstance(items, list):
            logger.error(f"❌ JSON 파일 형식 오류: 리스트가 아닙니다")
            return {"posts_collected": 0, "comments_collected": 0, "errors": ["Invalid JSON format"]}
        
        logger.info(f"  {len(items)}개 아이템 읽기 완료")
        
        # 데이터베이스에 저장
        stats = process_apify_results(items, keyword, run_id)
        
        logger.info(f"  ✅ {keyword}: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
        return stats
        
    except FileNotFoundError:
        logger.error(f"❌ 파일을 찾을 수 없습니다: {json_file_path}")
        return {"posts_collected": 0, "comments_collected": 0, "errors": [f"File not found: {json_file_path}"]}
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 파싱 오류: {e}")
        return {"posts_collected": 0, "comments_collected": 0, "errors": [f"JSON decode error: {e}"]}
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
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
    
    # DATABASE_URL 확인
    db_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    if not db_url:
        logger.error("❌ DATABASE_URL이 설정되지 않았습니다.")
        logger.error("   export DATABASE_URL='postgresql://...'")
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
    logger.info(f"총 {len(COLLECTED_DATASETS)}개 키워드 중 첫 번째 키워드만 처리")
    logger.info(f"{'='*60}\n")
    
    # 첫 번째 키워드만 처리
    for idx, dataset_info in enumerate(COLLECTED_DATASETS[:1], 1):
        keyword = dataset_info["keyword"]
        dataset_id = dataset_info["dataset_id"]
        
        logger.info(f"\n[{idx}/{len(COLLECTED_DATASETS)}] Processing: {keyword}")
        logger.info(f"  Dataset ID: {dataset_id}")
        
        # JSON 파일 경로 확인 (data/ 폴더에 저장되어 있다고 가정)
        safe_keyword = keyword.replace(' ', '_').replace('/', '_')
        json_file = project_root / "data" / f"{safe_keyword}_{dataset_id}.json"
        
        if json_file.exists():
            # JSON 파일에서 읽기
            logger.info(f"  📂 기존 JSON 파일 사용: {json_file}")
            stats = save_dataset_from_json_file(str(json_file), keyword, run_id)
        else:
            # Apify API로 데이터 가져와서 JSON으로 저장
            logger.info(f"  📥 Apify API로 데이터 다운로드 중...")
            json_file_path = download_dataset_to_json(apify_client, dataset_id, keyword)
            
            if json_file_path and json_file_path.exists():
                # JSON 파일에서 읽어서 DB에 저장
                stats = save_dataset_from_json_file(str(json_file_path), keyword, run_id)
            else:
                logger.error(f"  ❌ 데이터 다운로드 실패")
                stats = {"posts_collected": 0, "comments_collected": 0, "errors": [f"Failed to download dataset {dataset_id}"]}
        
        if stats.get("posts_collected", 0) > 0:
            total_stats["keywords_processed"] += 1
            total_stats["total_posts"] += stats["posts_collected"]
            total_stats["total_comments"] += stats["comments_collected"]
        
        if stats.get("errors"):
            total_stats["errors"].extend(stats["errors"])
    
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
