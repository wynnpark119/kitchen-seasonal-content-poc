"""
Worker 메인 스크립트
데이터 수집/분석 파이프라인 실행
Railway에서 백그라운드로 실행되는 worker 서비스
"""
import os
import sys
import time
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.run_pipeline import (
    run_collect_mode,
    run_ingest_gsc_mode,
    run_analyze_mode,
    run_label_mode,
)
from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.logging import setup_logger

logger = setup_logger("worker.main")

# save_all_keywords_api 모듈 임포트 (선택적)
try:
    from save_all_keywords_api import (
        COLLECTED_DATASETS,
        check_database_connection,
        fetch_dataset_items,
        save_dataset
    )
    SAVE_KEYWORDS_AVAILABLE = True
except ImportError as e:
    SAVE_KEYWORDS_AVAILABLE = False
    logger.warning(f"save_all_keywords_api 모듈을 찾을 수 없습니다: {e}. 키워드 저장 기능을 사용할 수 없습니다.")

def run_pipeline(mode: str, dry_run: bool = False, **kwargs):
    """
    파이프라인 실행
    
    Args:
        mode: 실행 모드 (collect, ingest_gsc, analyze, label, all)
        dry_run: Dry run 모드 여부
        **kwargs: 추가 옵션 (gsc_csv, collect_mode, max_docs, max_briefs)
    """
    run_id = create_pipeline_run(mode, status="running")
    logger.info(f"Pipeline run started: run_id={run_id}, mode={mode}, dry_run={dry_run}")
    
    if dry_run:
        logger.info("*** DRY RUN MODE: No database writes will be performed ***")
    
    try:
        stats = {}
        
        if mode == "collect":
            collect_mode = kwargs.get("collect_mode", "both")
            stats = run_collect_mode(run_id, dry_run, collect_mode)
        
        elif mode == "ingest_gsc":
            gsc_csv = kwargs.get("gsc_csv")
            if not gsc_csv:
                raise ValueError("gsc_csv is required for ingest_gsc mode")
            stats = run_ingest_gsc_mode(run_id, gsc_csv, dry_run)
        
        elif mode == "analyze":
            max_docs = kwargs.get("max_docs")
            stats = run_analyze_mode(run_id, dry_run, max_docs)
        
        elif mode == "label":
            max_briefs = kwargs.get("max_briefs", 20)
            stats = run_label_mode(run_id, dry_run, max_briefs)
        
        elif mode == "save_keywords":
            # Apify 데이터셋에서 키워드 데이터 저장
            if not SAVE_KEYWORDS_AVAILABLE:
                raise ImportError("save_all_keywords_api 모듈을 찾을 수 없습니다.")
            logger.info("Running save_keywords mode: Saving all collected keywords from Apify datasets...")
            
            # 환경 변수 확인
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token:
                raise ValueError("APIFY_API_TOKEN이 설정되지 않았습니다.")
            
            # 데이터베이스 연결 확인
            if not check_database_connection():
                raise ValueError("데이터베이스 연결 실패")
            
            # Apify 클라이언트 초기화
            from apify_client import ApifyClient
            apify_client = ApifyClient(apify_token)
            logger.info("✅ Apify 클라이언트 초기화 완료")
            
            # 통계 초기화
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
                    result_stats = save_dataset(apify_client, dataset_id, keyword, run_id)
                    
                    total_stats["keywords_processed"] += 1
                    total_stats["total_posts"] += result_stats["posts_collected"]
                    total_stats["total_comments"] += result_stats["comments_collected"]
                    if result_stats.get("errors"):
                        total_stats["errors"].extend(result_stats["errors"])
                        
                except Exception as e:
                    logger.error(f"  ❌ Fatal error processing {keyword}: {e}", exc_info=True)
                    total_stats["errors"].append(f"{keyword}: {str(e)}")
            
            logger.info(f"\n{'='*60}")
            logger.info("저장 완료!")
            logger.info(f"  처리된 키워드: {total_stats['keywords_processed']}/{len(COLLECTED_DATASETS)}")
            logger.info(f"  총 포스트: {total_stats['total_posts']}")
            logger.info(f"  총 댓글: {total_stats['total_comments']}")
            if total_stats["errors"]:
                logger.warning(f"  오류: {len(total_stats['errors'])}개")
            logger.info(f"{'='*60}\n")
            
            stats = total_stats
        
        elif mode == "all":
            logger.info("Running full pipeline (all modes)...")
            all_stats = {}
            
            # Collect
            all_stats["collect"] = run_collect_mode(run_id, dry_run, kwargs.get("collect_mode", "both"))
            
            # Ingest GSC (if CSV path provided)
            gsc_csv = kwargs.get("gsc_csv")
            if gsc_csv:
                all_stats["ingest_gsc"] = run_ingest_gsc_mode(run_id, gsc_csv, dry_run)
            else:
                logger.warning("GSC CSV path not provided, skipping GSC ingestion")
                all_stats["ingest_gsc"] = {"skipped": True, "message": "No gsc_csv provided"}
            
            # Analyze
            all_stats["analyze"] = run_analyze_mode(run_id, dry_run, kwargs.get("max_docs"))
            
            # Label
            all_stats["label"] = run_label_mode(run_id, dry_run, kwargs.get("max_briefs", 20))
            
            stats = all_stats
        
        # Update pipeline run as completed
        update_pipeline_run(run_id, "completed", metadata=stats)
        logger.info(f"Pipeline run completed successfully: run_id={run_id}")
        return stats
    
    except Exception as e:
        logger.error(f"Pipeline run failed: {e}", exc_info=True)
        update_pipeline_run(run_id, "failed", error_message=str(e))
        raise

def main():
    """Worker 메인 함수 - Railway에서 백그라운드로 실행"""
    # 환경 변수에서 실행 모드 가져오기 (기본값: collect)
    # Railway 환경 변수에서 설정 가능: WORKER_MODE=collect|analyze|label|all
    worker_mode = os.getenv("WORKER_MODE", "collect")
    
    # 실행 간격 설정 (초 단위, 기본값: 3600 = 1시간)
    # Railway 환경 변수에서 설정 가능: WORKER_INTERVAL=3600
    worker_interval = int(os.getenv("WORKER_INTERVAL", "3600"))
    
    # 한 번만 실행할지 여부 (기본값: False = 반복 실행)
    # Railway 환경 변수에서 설정 가능: WORKER_ONCE=true
    run_once = os.getenv("WORKER_ONCE", "false").lower() == "true"
    
    # Dry run 모드 (기본값: False)
    dry_run = os.getenv("WORKER_DRY_RUN", "false").lower() == "true"
    
    # 추가 옵션들
    gsc_csv = os.getenv("WORKER_GSC_CSV", None)
    collect_mode = os.getenv("WORKER_COLLECT_MODE", "both")  # serp_only, reddit_only, both
    max_docs = os.getenv("WORKER_MAX_DOCS", None)
    max_briefs = int(os.getenv("WORKER_MAX_BRIEFS", "20"))
    
    if max_docs:
        max_docs = int(max_docs)
    
    logger.info(f"Worker 시작")
    logger.info(f"  모드: {worker_mode}")
    logger.info(f"  간격: {worker_interval}초")
    logger.info(f"  한 번만 실행: {run_once}")
    logger.info(f"  Dry run: {dry_run}")
    if gsc_csv:
        logger.info(f"  GSC CSV: {gsc_csv}")
    
    kwargs = {
        "gsc_csv": gsc_csv,
        "collect_mode": collect_mode,
        "max_docs": max_docs,
        "max_briefs": max_briefs,
    }
    
    while True:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"파이프라인 실행 시작: {worker_mode}")
            logger.info(f"{'='*60}\n")
            
            # 파이프라인 실행
            run_pipeline(worker_mode, dry_run=dry_run, **kwargs)
            
            logger.info(f"\n파이프라인 실행 완료: {worker_mode}")
            
            # 한 번만 실행하도록 설정된 경우 종료
            if run_once:
                logger.info("WORKER_ONCE=true로 설정되어 종료합니다.")
                break
            
            # 다음 실행까지 대기
            logger.info(f"\n다음 실행까지 {worker_interval}초 대기 중...")
            time.sleep(worker_interval)
            
        except KeyboardInterrupt:
            logger.info("\nWorker 종료 신호 수신")
            break
        except Exception as e:
            logger.error(f"\n오류 발생: {e}", exc_info=True)
            
            # 한 번만 실행하도록 설정된 경우 종료
            if run_once:
                logger.info("WORKER_ONCE=true로 설정되어 종료합니다.")
                break
            
            # 오류 발생 시에도 다음 실행까지 대기 (짧은 간격)
            error_interval = min(worker_interval, 300)  # 최대 5분
            logger.info(f"\n오류 후 {error_interval}초 후 재시도...")
            time.sleep(error_interval)

if __name__ == "__main__":
    main()
