#!/usr/bin/env python3
"""
20개 키워드의 Apify 데이터셋을 JSON 파일로 다운로드하는 스크립트
Apify Python SDK를 사용하여 API로 데이터를 가져옵니다.

사용법:
    export APIFY_API_TOKEN="your-apify-token"
    또는 .env 파일에 APIFY_API_TOKEN 설정
    python download_keywords_json.py
"""
import os
import sys
import json
from pathlib import Path
from apify_client import ApifyClient

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드 (dotenv가 있으면 사용, 없으면 직접 읽기)
env_path = project_root / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path)
    except ImportError:
        # dotenv가 없으면 .env 파일을 직접 읽기
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # 이미 환경 변수가 설정되어 있지 않을 때만 설정
                    if key and not os.getenv(key):
                        os.environ[key] = value

from worker.pipeline.logging import setup_logger

logger = setup_logger("download_keywords_json")

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
            
            # ListPage 객체 처리 (딕셔너리 또는 객체)
            if hasattr(dataset_items, 'items'):
                # ListPage 객체인 경우
                batch_items = list(dataset_items.items)
            elif isinstance(dataset_items, dict):
                # 딕셔너리인 경우
                batch_items = list(dataset_items.get('items', []))
            else:
                # 직접 반복 가능한 경우
                batch_items = list(dataset_items)
            
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
            logger.error(f"  Error fetching items: {e}", exc_info=True)
            break
    
    return items

def download_dataset_to_json(apify_client: ApifyClient, dataset_id: str, keyword: str, overwrite: bool = False) -> Path:
    """
    Apify API를 사용하여 데이터셋을 가져와서 JSON 파일로 저장
    
    Args:
        apify_client: ApifyClient 인스턴스
        dataset_id: Apify dataset ID
        keyword: 키워드 (파일명에 사용)
        overwrite: 기존 파일이 있어도 덮어쓸지 여부
    
    Returns:
        저장된 JSON 파일 경로 (실패시 None)
    """
    logger.info(f"📥 Apify API로 데이터셋 가져오기: {dataset_id} (키워드: {keyword})")
    
    try:
        # 데이터셋 메타데이터 확인
        dataset_info = apify_client.dataset(dataset_id).get()
        item_count = dataset_info.get('itemCount', 0)
        logger.info(f"  Dataset has {item_count} items")
        
        # JSON 파일 경로 생성
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        
        safe_keyword = keyword.replace(' ', '_').replace('/', '_')
        json_file = data_dir / f"{safe_keyword}_{dataset_id}.json"
        
        # 기존 파일 확인
        if json_file.exists() and not overwrite:
            logger.info(f"  ⏭️  기존 파일이 있습니다: {json_file}")
            logger.info(f"     건너뜁니다. (덮어쓰려면 overwrite=True 사용)")
            return json_file
        
        # 모든 아이템 가져오기
        items = fetch_dataset_items(apify_client, dataset_id)
        
        if not items:
            logger.warning(f"  ⚠️  No items found in dataset {dataset_id}")
            return None
        
        # JSON 파일로 저장
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        logger.info(f"  ✅ {len(items)}개 아이템을 JSON 파일로 저장: {json_file}")
        return json_file
        
    except Exception as e:
        logger.error(f"  ❌ Error downloading dataset {dataset_id}: {e}", exc_info=True)
        return None

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
    
    # Apify 클라이언트 초기화
    apify_client = ApifyClient(apify_token)
    logger.info("✅ Apify 클라이언트 초기화 완료")
    
    # data 디렉토리 생성
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    total_stats = {
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "total_items": 0,
        "errors": []
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"총 {len(COLLECTED_DATASETS)}개 키워드 데이터 JSON 다운로드 시작")
    logger.info(f"{'='*60}\n")
    
    # 각 키워드 처리
    for idx, dataset_info in enumerate(COLLECTED_DATASETS, 1):
        keyword = dataset_info["keyword"]
        dataset_id = dataset_info["dataset_id"]
        
        logger.info(f"\n[{idx}/{len(COLLECTED_DATASETS)}] Processing: {keyword}")
        logger.info(f"  Dataset ID: {dataset_id}")
        
        try:
            json_file = download_dataset_to_json(apify_client, dataset_id, keyword, overwrite=False)
            
            if json_file:
                if json_file.exists():
                    # 파일 크기 확인
                    file_size = json_file.stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                    
                    # 아이템 수 확인
                    with open(json_file, 'r', encoding='utf-8') as f:
                        items = json.load(f)
                        item_count = len(items) if isinstance(items, list) else 0
                    
                    total_stats["downloaded"] += 1
                    total_stats["total_items"] += item_count
                    logger.info(f"  📊 파일 크기: {file_size_mb:.2f} MB, 아이템 수: {item_count}")
                else:
                    total_stats["skipped"] += 1
            else:
                total_stats["failed"] += 1
                total_stats["errors"].append(f"{keyword} ({dataset_id}): Download failed")
                
        except Exception as e:
            logger.error(f"  ❌ Fatal error processing {keyword}: {e}", exc_info=True)
            total_stats["failed"] += 1
            total_stats["errors"].append(f"{keyword}: {str(e)}")
    
    logger.info(f"\n{'='*60}")
    logger.info("다운로드 완료!")
    logger.info(f"  다운로드 성공: {total_stats['downloaded']}/{len(COLLECTED_DATASETS)}")
    logger.info(f"  건너뜀: {total_stats['skipped']}")
    logger.info(f"  실패: {total_stats['failed']}")
    logger.info(f"  총 아이템 수: {total_stats['total_items']}")
    if total_stats["errors"]:
        logger.warning(f"  오류: {len(total_stats['errors'])}개")
        for error in total_stats["errors"]:
            logger.warning(f"    - {error}")
    logger.info(f"{'='*60}\n")

if __name__ == "__main__":
    main()
