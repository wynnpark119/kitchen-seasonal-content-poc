"""
SERP AI Overview collection via SerpAPI
"""
import os
import time
import json
from typing import List, Dict, Any
from serpapi import GoogleSearch
from .config import SERP_AIO_SAMPLE_QUERIES
from .db import upsert_serp_aio
from .logging import setup_logger

logger = setup_logger("collect_serp_aio")

def collect_serp_aio(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    Collect SERP AI Overview snapshots via SerpAPI
    
    샘플 수집: 각 대주제별 1개 쿼리만 (총 4개)
    """
    serpapi_key = os.getenv("SERPAPI_KEY")
    
    # In dry-run mode, skip key check
    if not dry_run and not serpapi_key:
        raise ValueError("SERPAPI_KEY not found in environment variables")
    
    stats = {
        "queries_processed": 0,
        "aio_available": 0,
        "aio_not_available": 0,
        "aio_errors": 0,
        "errors": []
    }
    
    # 샘플 쿼리 4개 (각 대주제 1개씩)
    sample_queries = list(SERP_AIO_SAMPLE_QUERIES.values())
    
    logger.info(f"Starting SERP AIO collection for {len(sample_queries)} sample queries")
    
    for query in sample_queries:
        try:
            logger.info(f"Collecting SERP AIO for query: {query}")
            
            if dry_run:
                logger.info(f"[DRY RUN] Would query SerpAPI for '{query}'")
                logger.info(f"[DRY RUN] Would check AI Overview availability and length")
                stats["queries_processed"] += 1
                continue
            
            params = {
                "q": query,
                "api_key": serpapi_key,
                "engine": "google",
                "hl": "en",
                "gl": "us"
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check for AI Overview
            aio_status = "NOT_AVAILABLE"
            aio_data = {
                "aio_text": None,
                "cited_sources_json": None,
                "locale": "en-US",
                "raw_json": json.dumps(results)
            }
            
            try:
                if "ai_overview" in results and results["ai_overview"]:
                    aio_overview = results["ai_overview"]
                    aio_text = aio_overview.get("text", "") or aio_overview.get("answer", "")
                    
                    if aio_text:
                        aio_status = "AVAILABLE"
                        aio_data["aio_text"] = aio_text
                        aio_data["cited_sources_json"] = json.dumps(aio_overview.get("cited_sources", []))
                        stats["aio_available"] += 1
                        logger.info(f"Found AI Overview for '{query}' (length: {len(aio_text)} chars, sources: {len(aio_overview.get('cited_sources', []))})")
                    else:
                        logger.info(f"AI Overview structure found but no text for '{query}'")
                        stats["aio_not_available"] += 1
                else:
                    logger.info(f"No AI Overview found for '{query}' (NOT_AVAILABLE)")
                    stats["aio_not_available"] += 1
                
            except Exception as e:
                aio_status = "ERROR"
                stats["aio_errors"] += 1
                logger.error(f"Error processing AI Overview for '{query}': {e}")
                aio_data["raw_json"] = json.dumps({"error": str(e), "raw_results": results})
            
            # Save to database
            upsert_serp_aio(query, aio_data, run_id, aio_status)
            stats["queries_processed"] += 1
            
            # Rate limiting
            time.sleep(1)
        
        except Exception as e:
            logger.error(f"Error collecting SERP AIO for query '{query}': {e}")
            stats["errors"].append(str(e))
            stats["aio_errors"] += 1
    
    logger.info(f"SERP AIO collection completed:")
    logger.info(f"  Queries processed: {stats['queries_processed']}")
    logger.info(f"  AVAILABLE: {stats['aio_available']}")
    logger.info(f"  NOT_AVAILABLE: {stats['aio_not_available']}")
    logger.info(f"  ERROR: {stats['aio_errors']}")
    
    return stats
