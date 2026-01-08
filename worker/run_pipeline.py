#!/usr/bin/env python3
"""
Pipeline entry point: End-to-end data collection, processing, and analysis

Usage:
    python run_pipeline.py --mode=all
    python run_pipeline.py --mode=collect
    python run_pipeline.py --mode=ingest_gsc --gsc-csv path/to/file.csv
    python run_pipeline.py --mode=analyze
    python run_pipeline.py --mode=label
    python run_pipeline.py --mode=all --dry-run

Execution modes:
    --mode=collect       Reddit + SERP AIO collection/ingestion
    --mode=ingest_gsc    GSC CSV loading/ingestion
    --mode=analyze       Preprocessing/embedding/clustering/keywords/timeseries
    --mode=label         LLM-based cluster labeling and brief generation
    --mode=all           Full pipeline execution

Options:
    --dry-run           Dry run mode (no DB writes, sample output only)
    --gsc-csv PATH      Path to GSC CSV file (required for ingest_gsc mode)
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run, update_pipeline_run
from worker.pipeline.logging import setup_logger
from worker.pipeline.collect_reddit import collect_reddit_data
from worker.pipeline.collect_serp_aio import collect_serp_aio
from worker.pipeline.ingest_gsc import ingest_gsc_csv
from worker.pipeline.preprocess import preprocess_reddit_posts
from worker.pipeline.embedding import generate_embeddings
from worker.pipeline.clustering import run_clustering_pipeline
from worker.pipeline.keywords import extract_keywords_for_all_clusters
from worker.pipeline.timeseries import generate_timeseries
from worker.pipeline.labeling import generate_briefs
from worker.pipeline.scoring import calculate_scores

logger = setup_logger("run_pipeline")

def run_collect_mode(run_id: int, dry_run: bool = False):
    """Run data collection mode"""
    logger.info("=" * 60)
    logger.info("MODE: COLLECT - Reddit + SERP AIO Collection")
    logger.info("=" * 60)
    
    stats = {}
    
    # Collect Reddit data
    logger.info("Starting Reddit collection...")
    reddit_stats = collect_reddit_data(run_id, dry_run)
    stats["reddit"] = reddit_stats
    logger.info(f"Reddit collection: {reddit_stats['posts_collected']} posts, {reddit_stats['comments_collected']} comments")
    
    # Collect SERP AIO
    logger.info("Starting SERP AIO collection...")
    serp_stats = collect_serp_aio(run_id, dry_run)
    stats["serp"] = serp_stats
    logger.info(f"SERP AIO collection: {serp_stats['aio_found']} AIO found")
    
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

def run_analyze_mode(run_id: int, dry_run: bool = False):
    """Run analysis mode"""
    logger.info("=" * 60)
    logger.info("MODE: ANALYZE - Preprocessing/Embedding/Clustering/Timeseries")
    logger.info("=" * 60)
    
    stats = {}
    
    # Preprocess
    logger.info("Starting preprocessing...")
    preprocess_stats = preprocess_reddit_posts(run_id, dry_run)
    stats["preprocess"] = preprocess_stats
    logger.info(f"Preprocessing: {preprocess_stats['cleaned_posts']} posts cleaned")
    
    # Generate embeddings
    logger.info("Starting embedding generation...")
    embedding_stats = generate_embeddings(run_id, dry_run)
    stats["embedding"] = embedding_stats
    logger.info(f"Embeddings: {embedding_stats['embeddings_created']} embeddings created")
    
    # Clustering
    logger.info("Starting clustering...")
    cluster_stats = run_clustering_pipeline(run_id, dry_run)
    stats["clustering"] = cluster_stats
    logger.info(f"Clustering: {cluster_stats['clusters_created']} clusters, {cluster_stats.get('noise_points', 0)} noise points")
    
    # Extract keywords
    logger.info("Starting keyword extraction...")
    keyword_stats = extract_keywords_for_all_clusters(run_id, dry_run)
    stats["keywords"] = keyword_stats
    logger.info(f"Keywords: {keyword_stats['keywords_extracted']} keywords extracted")
    
    # Generate timeseries
    logger.info("Starting timeseries generation...")
    timeseries_stats = generate_timeseries(run_id, dry_run)
    stats["timeseries"] = timeseries_stats
    logger.info(f"Timeseries: {timeseries_stats['months_aggregated']} month records created")
    
    return stats

def run_label_mode(run_id: int, dry_run: bool = False):
    """Run labeling mode"""
    logger.info("=" * 60)
    logger.info("MODE: LABEL - LLM-based Cluster Labeling")
    logger.info("=" * 60)
    
    # Generate briefs
    logger.info("Starting brief generation...")
    brief_stats = generate_briefs(run_id, dry_run)
    logger.info(f"Briefs: {brief_stats['briefs_created']} briefs created")
    
    # Calculate scores
    logger.info("Starting score calculation...")
    score_stats = calculate_scores(run_id, dry_run)
    logger.info(f"Scores: {score_stats['briefs_scored']} briefs scored")
    
    return {"briefs": brief_stats, "scores": score_stats}

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Kitchen Seasonal Content POC Pipeline")
    parser.add_argument("--mode", choices=["collect", "ingest_gsc", "analyze", "label", "all"],
                       required=True, help="Execution mode")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no DB writes)")
    parser.add_argument("--gsc-csv", type=str, help="Path to GSC CSV file (required for ingest_gsc mode)")
    
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
            stats = run_collect_mode(run_id, args.dry_run)
        
        elif args.mode == "ingest_gsc":
            if not args.gsc_csv:
                raise ValueError("--gsc-csv path is required for ingest_gsc mode")
            stats = run_ingest_gsc_mode(run_id, args.gsc_csv, args.dry_run)
        
        elif args.mode == "analyze":
            stats = run_analyze_mode(run_id, args.dry_run)
        
        elif args.mode == "label":
            stats = run_label_mode(run_id, args.dry_run)
        
        elif args.mode == "all":
            # Run all modes sequentially
            logger.info("Running full pipeline (all modes)...")
            
            all_stats = {}
            
            # Collect
            all_stats["collect"] = run_collect_mode(run_id, args.dry_run)
            
            # Analyze
            all_stats["analyze"] = run_analyze_mode(run_id, args.dry_run)
            
            # Label
            all_stats["label"] = run_label_mode(run_id, args.dry_run)
            
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
