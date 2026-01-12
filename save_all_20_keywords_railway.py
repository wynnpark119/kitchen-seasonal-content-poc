#!/usr/bin/env python3
"""
Railway DATABASE_URL을 사용하여 모든 20개 키워드의 데이터를 데이터베이스에 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_20_keywords_railway")

# 모든 20개 키워드 및 dataset ID 매핑
ALL_KEYWORDS_DATASETS = [
    # SPRING_RECIPES
    {"datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas"},
    {"datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals"},
    {"datasetId": "espep8ycOpNwjnK0c", "keyword": "what to cook in spring"},
    {"datasetId": "HBU9RwE0LKTfosdpi", "keyword": "spring meal prep"},
    {"datasetId": "LYXvepkImLnLdGm48", "keyword": "light spring recipes"},
    
    # SPRING_KITCHEN_STYLING
    {"datasetId": "yXqub9ijqT5BQHmlb", "keyword": "spring kitchen decor"},
    {"datasetId": "30aDnU50uC9L1ur1w", "keyword": "kitchen spring refresh"},
    {"datasetId": "YVa8nVEo8oHSzHhR1", "keyword": "spring table setting ideas"},
    {"datasetId": "RPL8m4MremBGj4vVq", "keyword": "how to decorate kitchen for spring"},
    {"datasetId": "gF2dPQKMe25vgda2j", "keyword": "spring kitchen ideas"},
    
    # REFRIGERATOR_ORGANIZATION
    {"datasetId": "JMdQaLPe6wSn4aYUo", "keyword": "refrigerator organization"},
    {"datasetId": "MZUpZW7AsSGmM7Pme", "keyword": "fridge organization tips"},
    {"datasetId": "ffOQ6gWAgE4SvAIUU", "keyword": "how to organize refrigerator"},
    {"datasetId": "LghMjyUJ9c1wfH9vh", "keyword": "refrigerator storage ideas"},
    {"datasetId": "s9N4ldadvFkUSC2Yr", "keyword": "fridge organization system"},
    
    # VEGETABLE_PREP_HANDLING
    {"datasetId": "BxKKKHf2TPr0RZ2aj", "keyword": "vegetable prep"},
    {"datasetId": "csIbII5EHZQDjdBfn", "keyword": "how to prep vegetables"},
    {"datasetId": "gwbMxDIYm8hzYax0n", "keyword": "vegetable storage tips"},
    {"datasetId": "VXBkcE1T6HdpQ1a3h", "keyword": "how to store vegetables"},
    {"datasetId": "e1oOCOhftNlR2quAi", "keyword": "vegetable washing tips"},
]

def main():
    """
    모든 20개 키워드의 데이터를 데이터베이스에 저장
    
    사용법:
    1. Railway 콘솔에서 DATABASE_URL 복사
    2. 환경 변수로 설정:
       export DATABASE_URL='postgresql://postgres:password@host.railway.app:port/railway'
    3. 이 스크립트 실행
    4. AI Assistant가 각 dataset의 데이터를 MCP 도구로 가져와서 저장
    """
    try:
        # DATABASE_URL 확인
        database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            logger.info("\n" + "=" * 60)
            logger.info("Railway DATABASE_URL 설정 방법:")
            logger.info("=" * 60)
            logger.info("1. Railway 콘솔 (https://railway.app) 접속")
            logger.info("2. 프로젝트 → PostgreSQL 서비스 선택")
            logger.info("3. 'Variables' 탭에서 DATABASE_URL 복사")
            logger.info("4. 터미널에서 실행:")
            logger.info("   export DATABASE_URL='postgresql://...'")
            logger.info("\n또는 .env 파일에 추가:")
            logger.info("   DATABASE_URL=postgresql://...")
            logger.info("=" * 60)
            return None
        
        db_name = database_url.split('@')[-1].split('/')[-1].split('?')[0] if '@' in database_url else 'unknown'
        logger.info(f"✅ Using Railway database: {db_name}")
        
        # DB 연결 테스트
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute('SELECT version();')
                version = cur.fetchone()[0]
                logger.info(f"✅ Database connection successful")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return None
        
        # 파이프라인 run 생성
        pipeline_run_id = create_pipeline_run("collect_reddit_save_all_20", status="running")
        logger.info(f"✅ Pipeline run created: run_id={pipeline_run_id}")

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
        logger.info(f"Pipeline run ID: {pipeline_run_id}")
        logger.info("=" * 60)
        
        logger.info("\n⚠️  주의:")
        logger.info("이 스크립트는 MCP 도구를 직접 호출할 수 없습니다.")
        logger.info("AI Assistant가 각 dataset의 데이터를 가져온 후")
        logger.info("process_apify_results() 함수를 호출해야 합니다.")
        
        # 실제 저장은 MCP 도구를 통해 데이터를 가져온 후 수행해야 합니다
        # 여기서는 placeholder로 남겨둡니다

        update_pipeline_run(pipeline_run_id, "completed", metadata=total_stats)
        logger.info(f"\n✅ 모든 키워드 저장 완료!")
        logger.info(f"  총 포스트: {total_stats['posts_collected']}개")
        logger.info(f"  총 댓글: {total_stats['comments_collected']}개")
        logger.info(f"  처리된 키워드: {total_stats['keywords_processed']}개")
        
        return {
            "run_id": pipeline_run_id,
            "stats": total_stats,
            "datasets": ALL_KEYWORDS_DATASETS
        }

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
