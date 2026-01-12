#!/usr/bin/env python3
"""
22개 run의 모든 데이터를 데이터베이스에 저장
각 run의 INPUT에서 키워드를 확인하고 저장
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_all_22_runs")

# 22개 run 정보 (run_id, dataset_id, key_value_store_id)
# 각 run의 INPUT에서 키워드를 확인해야 함
RUNS_INFO = [
    {"run_id": "FsxHPhDRLkHX7sIIO", "datasetId": "hYNaDehMRGFbLd9sW", "storeId": "y6jHTC40klvlCK8Jd", "keyword": "easy spring meals"},
    {"run_id": "EDIHhapgDr9MeKuo9", "datasetId": "Chej96NJu2xomUrg1", "storeId": "fWU9LnH1a4zbhPxTy", "keyword": "spring dinner ideas"},
    {"run_id": "B4ZGgle4f7Sxn57oj", "datasetId": "e1oOCOhftNlR2quAi", "storeId": "3tY2eEj3HCJFKr38U"},
    {"run_id": "rB02EjeA284GIGdBv", "datasetId": "VXBkcE1T6HdpQ1a3h", "storeId": "M83gatomfuQUUdw1f"},
    {"run_id": "E5Wbeu9qZNPdmHVde", "datasetId": "gwbMxDIYm8hzYax0n", "storeId": "0icUy557nbvcmfCKJ"},
    {"run_id": "H2i9r1n72nDK6tKqE", "datasetId": "csIbII5EHZQDjdBfn", "storeId": "GRZwt8vWPkWFttY88"},
    {"run_id": "S9XXqLOuqT07VjbIO", "datasetId": "BxKKKHf2TPr0RZ2aj", "storeId": "MJ1Ng573sdoD9Lc47"},
    {"run_id": "YLQ3LfWGq68FI0WJa", "datasetId": "s9N4ldadvFkUSC2Yr", "storeId": "7GxmMqAboeHHEbPQd"},
    {"run_id": "OMVaruQKYhfzdLG6v", "datasetId": "LghMjyUJ9c1wfH9vh", "storeId": "pDT7gbOHDYCgNgVNw"},
    {"run_id": "3LLkEW4ia8f8icL61", "datasetId": "ffOQ6gWAgE4SvAIUU", "storeId": "VcmdDznGz0imqYq8M"},
    {"run_id": "AuZYh2r54y1VuKllj", "datasetId": "MZUpZW7AsSGmM7Pme", "storeId": "OEQh3eGXdeaU3Zxb7"},
    {"run_id": "Y3JPschU2EeyBRj1R", "datasetId": "JMdQaLPe6wSn4aYUo", "storeId": "rg0BbqLJwXhrUMyha"},
    {"run_id": "rhS5MhGU6PmqGTFwc", "datasetId": "gF2dPQKMe25vgda2j", "storeId": "21PqBuhfzYzwQbkd4"},
    {"run_id": "YeeFQm8dzaMqT8anf", "datasetId": "RPL8m4MremBGj4vVq", "storeId": "Mc4vjGUN8DFb5aS4f"},
    {"run_id": "QWPru6wp0nukBGfs6", "datasetId": "YVa8nVEo8oHSzHhR1", "storeId": "DdPT9iapUaZq5hxJW"},
    {"run_id": "D5k1JLKOHb8nygUdu", "datasetId": "30aDnU50uC9L1ur1w", "storeId": "XjsEx9lEA9zlLqP74"},
    {"run_id": "d6EZ7ZhMLVwBeOnui", "datasetId": "yXqub9ijqT5BQHmlb", "storeId": "a0flmzM4cW83ImZzI"},
    {"run_id": "x2ZxITDo9d3fTqRXi", "datasetId": "mYY4sLNbDhf72uyje", "storeId": "YQdCjdSRqClKrV1yB"},
    {"run_id": "erqL8O8QBXS99P1Yd", "datasetId": "8OvEjBKAqUBrGyGgL", "storeId": "wsY4jvMEgUKuRt9TL"},
    {"run_id": "g3JL67O7G6Dhw0OFj", "datasetId": "LYXvepkImLnLdGm48", "storeId": "B0u0C7HlPqAMN9qqR"},
    {"run_id": "F0IQtYzT3xHn9BKTi", "datasetId": "HBU9RwE0LKTfosdpi", "storeId": "dr2ZeOFwFac9w99on"},
    {"run_id": "MRGTSEIJJGP6zP4vi", "datasetId": "espep8ycOpNwjnK0c", "storeId": "doe8zaGbMcFAkgKY0"},
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
        return
    
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
    for run_info in RUNS_INFO:
        run_id_str = run_info["run_id"]
        dataset_id = run_info["datasetId"]
        store_id = run_info.get("storeId")
        keyword = run_info.get("keyword")
        
        logger.info(f"\nProcessing run {run_id_str}")
        logger.info(f"  Dataset ID: {dataset_id}")
        logger.info(f"  Store ID: {store_id}")
        logger.info(f"  Keyword: {keyword or 'Need to fetch from INPUT'}")
        
        # 키워드가 없으면 INPUT에서 가져오기
        if not keyword and store_id:
            logger.info(f"  → Need to fetch keyword from INPUT (store: {store_id})")
        
        # MCP 도구를 사용하여 전체 데이터 가져오기
        # mcp_apify_get-actor-output(datasetId=dataset_id, offset=0, limit=1000)
        # 그 다음 process_apify_results(items, keyword, pipeline_run_id) 호출
    
    logger.info("\n" + "=" * 60)
    logger.info("다음 단계:")
    logger.info("1. 각 run의 INPUT에서 키워드 확인 (mcp_apify_get-key-value-store-record)")
    logger.info("2. 각 dataset의 전체 데이터 가져오기 (mcp_apify_get-actor-output)")
    logger.info("3. process_apify_results(items, keyword, pipeline_run_id) 호출하여 저장")
    logger.info("=" * 60)
    
    return pipeline_run_id

if __name__ == "__main__":
    run_id = main()
    if run_id:
        print(f"\nPipeline run_id: {run_id}")
        print("이제 각 run의 키워드를 확인하고 데이터를 저장하세요.")
