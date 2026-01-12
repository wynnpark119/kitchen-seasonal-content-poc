#!/usr/bin/env python3
"""
Pipeline entry point: End-to-end data collection, processing, and analysis

이 파이프라인은 Reddit, Google SERP AI Overview, Google Search Console 데이터를
수집하고 분석하여 키친 라이프스타일 콘텐츠 주제를 발굴합니다.

실행 예시:
    # 전체 파이프라인 실행
    python worker/run_pipeline.py --mode=all
    
    # 개별 모드 실행
    python worker/run_pipeline.py --mode=collect
    python worker/run_pipeline.py --mode=ingest_gsc --gsc-csv data/gsc_2024.csv
    python worker/run_pipeline.py --mode=analyze
    python worker/run_pipeline.py --mode=label
    
    # Dry run (DB 쓰기 없이 테스트, 샘플 10개만)
    python worker/run_pipeline.py --mode=analyze --dry-run
    
    # 실제 실행 (비용 통제: 상위 반응 포스트 100개만)
    python worker/run_pipeline.py --mode=analyze --max-docs=100

Execution modes:
    --mode=collect       Reddit 수집 + SERP AIO 1회 스냅샷 수집
    --mode=ingest_gsc     GSC CSV 로딩 및 적재 (--gsc-csv 필수)
    --mode=analyze        정제/임베딩/클러스터링/특징어/시계열 생성
    --mode=label          클러스터 단위 LLM 해석 및 topic_qa_briefs 생성
    --mode=all            collect → ingest_gsc → analyze → label 전체 실행

Options:
    --dry-run           Dry run 모드 (DB 쓰기 없이 처리량/샘플만 로그 출력)
    --gsc-csv PATH      GSC CSV 파일 경로 (ingest_gsc 모드 필수)
    --max-docs N        최대 처리 문서 수 (비용 통제용, analyze 모드에서 상위 반응 포스트 N개만)

환경 변수:
    DATABASE_URL        PostgreSQL 연결 URL
    OPENAI_API_KEY      OpenAI API 키 (임베딩 및 LLM)
    APIFY_TOKEN         Apify API 토큰 (Reddit 수집)
    SERPAPI_KEY         SerpAPI 키 (SERP AIO 수집)

재실행 안정성:
    - 모든 쓰기 작업은 upsert/unique key 기반 처리
    - 동일 run_id로 재실행해도 중복 생성되지 않음
    - pipeline_runs 테이블에 실행 상태/에러/처리 건수 기록
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.logging import setup_logger
from worker.pipeline.collect_reddit import collect_reddit_data
from worker.pipeline.collect_serp_aio import collect_serp_aio
from worker.pipeline.ingest_gsc import ingest_gsc_csv
from worker.pipeline.preprocess import preprocess_reddit_posts
# DEPRECATED: Post-level embedding (비활성화)
# from worker.pipeline.embedding import generate_embeddings
# from worker.pipeline.clustering import run_clustering_pipeline
from worker.pipeline.tfidf_clustering import run_tfidf_clustering
from worker.pipeline.generate_serp_queries import generate_serp_queries_for_all_clusters
from worker.pipeline.collect_serp_results import collect_serp_results_for_all_clusters
from worker.pipeline.cluster_embedding import generate_embeddings_for_all_clusters
from worker.pipeline.keywords import extract_keywords_for_all_clusters
from worker.pipeline.timeseries import generate_timeseries
from worker.pipeline.labeling import generate_briefs
from worker.pipeline.scoring import calculate_scores

logger = setup_logger("run_pipeline")

def run_collect_mode(run_id: int, dry_run: bool = False, collect_mode: str = "both"):
    """
    Run data collection mode
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
        collect_mode: "serp_only", "reddit_only", or "both" (default)
    """
    logger.info("=" * 60)
    logger.info(f"MODE: COLLECT - Collection mode: {collect_mode}")
    logger.info("=" * 60)
    
    stats = {}
    
    # Collect Reddit data (if not serp_only)
    if collect_mode in ["reddit_only", "both"]:
        logger.info("Starting Reddit collection via MCP...")
        logger.info("Note: Reddit collection uses Apify MCP tools.")
        logger.info("MCP calls will be made by the AI assistant.")
        
        reddit_stats = collect_reddit_data(run_id, dry_run)
        stats["reddit"] = reddit_stats
        logger.info(f"Reddit collection: {reddit_stats['posts_collected']} posts, {reddit_stats['comments_collected']} comments")
    else:
        logger.info("Skipping Reddit collection (serp_only mode)")
        stats["reddit"] = {"skipped": True}
    
    # Collect SERP AIO (if not reddit_only)
    if collect_mode in ["serp_only", "both"]:
        logger.info("Starting SERP AIO collection...")
        serp_stats = collect_serp_aio(run_id, dry_run)
        stats["serp"] = serp_stats
        logger.info(f"SERP AIO collection:")
        logger.info(f"  Queries processed: {serp_stats['queries_processed']}")
        logger.info(f"  AVAILABLE: {serp_stats.get('aio_available', 0)}")
        logger.info(f"  NOT_AVAILABLE: {serp_stats.get('aio_not_available', 0)}")
        logger.info(f"  ERROR: {serp_stats.get('aio_errors', 0)}")
    else:
        logger.info("Skipping SERP AIO collection (reddit_only mode)")
        stats["serp"] = {"skipped": True}
    
    return stats

def run_ingest_gsc_mode(run_id: int, csv_path: str, dry_run: bool = False):
    """Run GSC CSV ingestion mode"""
    logger.info("=" * 60)
    logger.info("MODE: INGEST_GSC - GSC CSV Ingestion")
    logger.info("=" * 60)
    
    if not csv_path:
        raise ValueError("--gsc-csv path is required for ingest_gsc mode")
    
    logger.info(f"Starting GSC CSV ingestion from: {csv_path}")
    stats = ingest_gsc_csv(csv_path, run_id, dry_run)
    logger.info(f"GSC ingestion: {stats['rows_inserted']} rows inserted")
    
    return stats

def run_analyze_mode(run_id: int, dry_run: bool = False, max_docs: Optional[int] = None):
    """
    Run analysis mode: preprocess -> embedding -> clustering
    
    순서:
    1. Preprocess: 텍스트 정제, 중복 제거
    2. Embedding: OpenAI 임베딩 생성 및 저장
    3. Clustering: HDBSCAN 클러스터링 및 대표 샘플 선정 (medoid 기준)
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
        max_docs: Maximum documents to process (cost control, None = all)
    """
    logger.info("=" * 60)
    logger.info("MODE: ANALYZE - Preprocessing/Embedding/Clustering")
    logger.info("=" * 60)
    if max_docs:
        logger.info(f"Cost control: Processing top {max_docs} posts by engagement")
    
    stats = {}
    
    # 1. Preprocess
    logger.info("Step 1: Starting preprocessing...")
    preprocess_stats = preprocess_reddit_posts(run_id, dry_run, max_docs=max_docs)
    stats["preprocess"] = preprocess_stats
    logger.info(f"Preprocessing completed:")
    logger.info(f"  Total posts: {preprocess_stats['total_posts']}")
    logger.info(f"  Title empty: {preprocess_stats.get('title_empty', 0)}")
    logger.info(f"  Too short: {preprocess_stats.get('too_short', 0)}")
    logger.info(f"  Deleted: {preprocess_stats.get('deleted', 0)}")
    logger.info(f"  Duplicates removed: {preprocess_stats.get('duplicates_removed', 0)}")
    logger.info(f"  Preprocessed: {preprocess_stats.get('preprocessed', 0)}")
    
    # 2. Generate embeddings
    logger.info("Step 2: Starting embedding generation...")
    embedding_stats = generate_embeddings(run_id, dry_run, max_docs=max_docs)
    stats["embedding"] = embedding_stats
    logger.info(f"Embedding generation completed:")
    logger.info(f"  Posts processed: {embedding_stats['posts_processed']}")
    logger.info(f"  Embeddings created: {embedding_stats['embeddings_created']}")
    logger.info(f"  Skipped (existing): {embedding_stats.get('skipped_existing', 0)}")
    logger.info(f"  Batches processed: {embedding_stats.get('batches_processed', 0)}")
    
    # 3. Clustering
    logger.info("Step 3: Starting clustering (medoid-based representative samples)...")
    cluster_stats = run_clustering_pipeline(run_id, dry_run)
    stats["clustering"] = cluster_stats
    logger.info(f"Clustering completed:")
    logger.info(f"  Clusters created: {cluster_stats.get('clusters_created', 0)}")
    logger.info(f"  Noise points: {cluster_stats.get('noise_points', 0)}")
    logger.info(f"  Assignments created: {cluster_stats.get('assignments_created', 0)}")
    logger.info(f"  Representative samples: {cluster_stats.get('representative_samples', 0)}")
    
    # Noise 비율 계산
    total_points = cluster_stats.get('assignments_created', 0) + cluster_stats.get('noise_points', 0)
    if total_points > 0:
        noise_ratio = cluster_stats.get('noise_points', 0) / total_points
        logger.info(f"  Noise ratio: {noise_ratio:.2%}")
    
    # 4. Timeseries (월 단위 시계열 생성, 카테고리별 시즌성 해석)
    logger.info("Step 4: Starting timeseries generation (with seasonality interpretation)...")
    timeseries_stats = generate_timeseries(run_id, dry_run)
    stats["timeseries"] = timeseries_stats
    logger.info(f"Timeseries generation completed:")
    logger.info(f"  Clusters processed: {timeseries_stats.get('clusters_processed', 0)}")
    logger.info(f"  Months aggregated: {timeseries_stats.get('months_aggregated', 0)}")
    logger.info(f"  Seasonal clusters: {timeseries_stats.get('seasonal_clusters', 0)}")
    logger.info(f"  Evergreen clusters: {timeseries_stats.get('evergreen_clusters', 0)}")
    
    return stats

def run_label_mode(run_id: int, dry_run: bool = False, max_briefs: int = 20):
    """
    Run labeling mode: LLM-based cluster labeling and brief generation
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
        max_briefs: Maximum number of briefs to generate (default: 20)
    """
    logger.info("=" * 60)
    logger.info("MODE: LABEL - LLM-based Cluster Labeling")
    logger.info("=" * 60)
    
    # Generate briefs (상위 N개 클러스터만)
    logger.info(f"Starting brief generation (max_briefs={max_briefs})...")
    brief_stats = generate_briefs(run_id, dry_run, max_briefs)
    logger.info(f"Brief generation completed:")
    logger.info(f"  Clusters processed: {brief_stats['clusters_processed']}")
    logger.info(f"  Briefs created: {brief_stats['briefs_created']}")
    if brief_stats.get('errors'):
        logger.warning(f"  Errors: {len(brief_stats['errors'])}")
    
    # Calculate scores
    logger.info("Starting score calculation...")
    score_stats = calculate_scores(run_id, dry_run)
    logger.info(f"Scoring completed: {score_stats['briefs_scored']} briefs scored")
    
    return {"briefs": brief_stats, "scores": score_stats}

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Kitchen Seasonal Content POC Pipeline")
    parser.add_argument("--mode", choices=[
        "collect", "ingest_gsc", "analyze", "label", "all",
        "cluster_tfidf", "generate_queries", "collect_serp", "embed_clusters", "cluster_pipeline"
    ], required=True, help="Execution mode")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no DB writes)")
    parser.add_argument("--gsc-csv", type=str, help="Path to GSC CSV file (required for ingest_gsc mode)")
    parser.add_argument("--collect", choices=["serp_only", "reddit_only", "both"],
                       default="both", help="Collection mode for --mode=collect (default: both)")
    parser.add_argument("--max-briefs", type=int, default=20,
                       help="Maximum number of briefs to generate for --mode=label (default: 20)")
    parser.add_argument("--max-docs", type=int, default=None,
                       help="Maximum documents to process for --mode=analyze (cost control, None = all)")
    
    args = parser.parse_args()
    
    # Create pipeline run
    run_type = args.mode
    run_id = create_pipeline_run(run_type, status="running")
    logger.info(f"Pipeline run started: run_id={run_id}, mode={run_type}, dry_run={args.dry_run}")
    
    if args.dry_run:
        logger.info("*** DRY RUN MODE: No database writes will be performed ***")
    
    try:
        # Execute based on mode
        if args.mode == "collect":
            stats = run_collect_mode(run_id, args.dry_run, args.collect)
        
        elif args.mode == "ingest_gsc":
            if not args.gsc_csv:
                raise ValueError("--gsc-csv path is required for ingest_gsc mode")
            stats = run_ingest_gsc_mode(run_id, args.gsc_csv, args.dry_run)
        
        elif args.mode == "analyze":
            stats = run_analyze_mode(run_id, args.dry_run, args.max_docs)
        
        elif args.mode == "label":
            stats = run_label_mode(run_id, args.dry_run, args.max_briefs)
        
        elif args.mode == "cluster_tfidf":
            stats = run_tfidf_clustering(run_id, args.dry_run)
        
        elif args.mode == "generate_queries":
            stats = generate_serp_queries_for_all_clusters(run_id, args.dry_run)
        
        elif args.mode == "collect_serp":
            stats = collect_serp_results_for_all_clusters(run_id, args.dry_run)
        
        elif args.mode == "embed_clusters":
            stats = generate_embeddings_for_all_clusters(run_id, args.dry_run)
        
        elif args.mode == "cluster_pipeline":
            # 새로운 클러스터 파이프라인 전체 실행
            logger.info("Running new cluster pipeline (TF-IDF clustering -> Query generation -> SERP collection -> Cluster embedding)...")
            all_stats = {}
            
            # 1. TF-IDF 클러스터링
            all_stats["cluster_tfidf"] = run_tfidf_clustering(run_id, args.dry_run)
            
            # 2. SERP 질문 생성
            all_stats["generate_queries"] = generate_serp_queries_for_all_clusters(run_id, args.dry_run)
            
            # 3. SERP 결과 수집
            all_stats["collect_serp"] = collect_serp_results_for_all_clusters(run_id, args.dry_run)
            
            # 4. 클러스터 임베딩
            all_stats["embed_clusters"] = generate_embeddings_for_all_clusters(run_id, args.dry_run)
            
            stats = all_stats
        
        elif args.mode == "all":
            # Run all modes sequentially
            logger.info("Running full pipeline (all modes)...")
            
            all_stats = {}
            
            # Collect (Reddit + SERP AIO)
            all_stats["collect"] = run_collect_mode(run_id, args.dry_run)
            
            # Ingest GSC (if CSV path provided)
            if args.gsc_csv:
                all_stats["ingest_gsc"] = run_ingest_gsc_mode(run_id, args.gsc_csv, args.dry_run)
            else:
                logger.warning("GSC CSV path not provided, skipping GSC ingestion")
                all_stats["ingest_gsc"] = {"skipped": True, "message": "No --gsc-csv provided"}
            
                # Analyze (정제/임베딩/클러스터링/시계열)
                all_stats["analyze"] = run_analyze_mode(run_id, args.dry_run, args.max_docs)
            
            # Label (LLM 기반 brief 생성)
                all_stats["label"] = run_label_mode(run_id, args.dry_run, args.max_briefs)
            
            stats = all_stats
        
        # Update pipeline run as completed
        update_pipeline_run(run_id, "completed", metadata=stats)
        logger.info(f"Pipeline run completed successfully: run_id={run_id}")
    
    except Exception as e:
        logger.error(f"Pipeline run failed: {e}", exc_info=True)
        update_pipeline_run(run_id, "failed", error_message=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
