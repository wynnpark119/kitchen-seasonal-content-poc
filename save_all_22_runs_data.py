#!/usr/bin/env python3
"""
22개 run의 모든 데이터를 데이터베이스에 저장
각 run의 키워드와 dataset ID를 확인하고 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_22_runs_data")

# 22개 run 정보 (키워드 확인 완료)
RUNS_DATA = [
    {"run_id": "FsxHPhDRLkHX7sIIO", "datasetId": "hYNaDehMRGFbLd9sW", "keyword": "easy spring meals"},
    {"run_id": "EDIHhapgDr9MeKuo9", "datasetId": "Chej96NJu2xomUrg1", "keyword": "spring dinner ideas"},
    {"run_id": "B4ZGgle4f7Sxn57oj", "datasetId": "e1oOCOhftNlR2quAi", "keyword": "vegetable washing tips"},
    {"run_id": "rB02EjeA284GIGdBv", "datasetId": "VXBkcE1T6HdpQ1a3h", "keyword": "how to store vegetables"},
    {"run_id": "E5Wbeu9qZNPdmHVde", "datasetId": "gwbMxDIYm8hzYax0n", "keyword": "vegetable storage tips"},
    {"run_id": "H2i9r1n72nDK6tKqE", "datasetId": "csIbII5EHZQDjdBfn", "keyword": "how to prep vegetables"},
    {"run_id": "S9XXqLOuqT07VjbIO", "datasetId": "BxKKKHf2TPr0RZ2aj", "keyword": "vegetable prep"},
    {"run_id": "YLQ3LfWGq68FI0WJa", "datasetId": "s9N4ldadvFkUSC2Yr", "keyword": "fridge organization system"},
    {"run_id": "OMVaruQKYhfzdLG6v", "datasetId": "LghMjyUJ9c1wfH9vh", "keyword": "refrigerator storage ideas"},
    {"run_id": "3LLkEW4ia8f8icL61", "datasetId": "ffOQ6gWAgE4SvAIUU", "keyword": "how to organize refrigerator"},
    {"run_id": "AuZYh2r54y1VuKllj", "datasetId": "MZUpZW7AsSGmM7Pme", "keyword": "fridge organization tips"},
    {"run_id": "Y3JPschU2EeyBRj1R", "datasetId": "JMdQaLPe6wSn4aYUo", "keyword": "refrigerator organization"},
    {"run_id": "rhS5MhGU6PmqGTFwc", "datasetId": "gF2dPQKMe25vgda2j", "keyword": "spring kitchen ideas"},
    {"run_id": "YeeFQm8dzaMqT8anf", "datasetId": "RPL8m4MremBGj4vVq", "keyword": "how to decorate kitchen for spring"},
    {"run_id": "QWPru6wp0nukBGfs6", "datasetId": "YVa8nVEo8oHSzHhR1", "keyword": "spring table setting ideas"},
    {"run_id": "D5k1JLKOHb8nygUdu", "datasetId": "30aDnU50uC9L1ur1w", "keyword": "kitchen spring refresh"},
    {"run_id": "d6EZ7ZhMLVwBeOnui", "datasetId": "yXqub9ijqT5BQHmlb", "keyword": "spring kitchen decor"},
    {"run_id": "x2ZxITDo9d3fTqRXi", "datasetId": "mYY4sLNbDhf72uyje", "keyword": "light spring recipes"},
    {"run_id": "erqL8O8QBXS99P1Yd", "datasetId": "8OvEjBKAqUBrGyGgL", "keyword": "spring meal prep"},
    {"run_id": "g3JL67O7G6Dhw0OFj", "datasetId": "LYXvepkImLnLdGm48", "keyword": "what to cook in spring"},
    {"run_id": "F0IQtYzT3xHn9BKTi", "datasetId": "HBU9RwE0LKTfosdpi", "keyword": "easy spring meals"},
    {"run_id": "MRGTSEIJJGP6zP4vi", "datasetId": "espep8ycOpNwjnK0c", "keyword": "spring dinner ideas"},
]

def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("22개 run의 데이터를 데이터베이스에 저장")
    logger.info("=" * 60)
    
    # DATABASE_URL 확인
    database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        logger.error("Please set DATABASE_URL or run this script in Railway environment")
        logger.info("\nRailway에서 실행하거나, 로컬에서 DATABASE_URL을 설정한 후 실행하세요.")
        return None
    
    # 파이프라인 run 생성
    pipeline_run_id = create_pipeline_run("collect", "running")
    logger.info(f"Pipeline run created: run_id={pipeline_run_id}")
    
    total_stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }
    
    # 각 run 처리
    for run_info in RUNS_DATA:
        run_id_str = run_info["run_id"]
        dataset_id = run_info["datasetId"]
        keyword = run_info["keyword"]
        
        logger.info(f"\nProcessing run {run_id_str}")
        logger.info(f"  Dataset ID: {dataset_id}")
        logger.info(f"  Keyword: {keyword}")
        
        # MCP 도구를 사용하여 전체 데이터 가져오기
        # mcp_apify_get-actor-output(datasetId=dataset_id, offset=0, limit=1000)
        # 그 다음 process_apify_results(items, keyword, pipeline_run_id) 호출
        
        logger.info(f"  → Use MCP tool to fetch all items from dataset {dataset_id}")
        logger.info(f"  → Then call process_apify_results(items, '{keyword}', {pipeline_run_id})")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"총 {len(RUNS_DATA)}개 run 처리 예정")
    logger.info("=" * 60)
    
    return pipeline_run_id

if __name__ == "__main__":
    run_id = main()
    if run_id:
        print(f"\nPipeline run_id: {run_id}")
        print("이제 각 dataset의 데이터를 가져와서 저장하세요.")
    else:
        print("\nDATABASE_URL이 설정되지 않았습니다.")
        print("Railway 환경에서 실행하거나 DATABASE_URL을 설정한 후 실행하세요.")
