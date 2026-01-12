#!/usr/bin/env python3
"""
주제별 클러스터링 실행 스크립트

각 topic_category별로 독립적으로 클러스터링을 수행합니다.
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any

# .env 파일 로드
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not os.getenv(key):
                            os.environ[key] = value
        except (PermissionError, IOError):
            pass

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection, create_pipeline_run, update_pipeline_run
from worker.pipeline.tfidf_clustering import run_tfidf_clustering
from worker.pipeline.logging import setup_logger

logger = setup_logger("run_category_clustering")

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("주제별 클러스터링 실행")
    print("=" * 80)
    
    # Pipeline run 생성
    run_id = create_pipeline_run("cluster_tfidf_category", status="running")
    logger.info(f"Pipeline run 생성: run_id={run_id}")
    
    print(f"\n실행 모드: 실제 DB 저장 (dry_run=False)")
    print(f"Run ID: {run_id}")
    print("\n각 topic_category별로 독립적으로 클러스터링 수행")
    print("=" * 80)
    
    try:
        # dry_run=False로 클러스터링 실행
        stats = run_tfidf_clustering(run_id, dry_run=False)
        
        # Pipeline run 완료 처리
        update_pipeline_run(run_id, "completed", metadata=stats)
        
        print("\n" + "=" * 80)
        print("클러스터링 완료")
        print("=" * 80)
        print(f"\n전체 결과:")
        print(f"  - 처리된 포스트 수: {stats.get('posts_processed', 0)}")
        print(f"  - 생성된 클러스터 수: {stats.get('clusters_created', 0)}")
        print(f"  - 생성된 할당 수: {stats.get('assignments_created', 0)}")
        
        print("\ntopic_category별 상세 결과:")
        for category, cat_stats in stats.get("categories", {}).items():
            if cat_stats.get("status") == "no_data":
                print(f"  {category}: 데이터 없음 (post 수: 0)")
            else:
                print(f"  {category}:")
                print(f"    - 포스트 수: {cat_stats.get('post_count', 0)}")
                print(f"    - 생성된 sub-cluster 수: {cat_stats.get('sub_clusters_created', 0)}")
        
        return 0
    
    except Exception as e:
        logger.error(f"클러스터링 실행 실패: {e}", exc_info=True)
        update_pipeline_run(run_id, "failed", error_message=str(e))
        raise

if __name__ == "__main__":
    sys.exit(main())
