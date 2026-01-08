"""
SERP AI Overview collection via SerpAPI
"""
import os
import time
from typing import List, Dict, Any
from serpapi import GoogleSearch
from .config import REDDIT_KEYWORDS
from .db import upsert_serp_aio
from .logging import setup_logger

logger = setup_logger("collect_serp_aio")

def collect_serp_aio(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Collect SERP AI Overview snapshots via SerpAPI"""
    serpapi_key = os.getenv("SERPAPI_KEY")
    
    # In dry-run mode, skip key check
    if not dry_run and not serpapi_key:
        raise ValueError("SERPAPI_KEY not found in environment variables")
    
    stats = {
        "queries_processed": 0,
        "aio_found": 0,
        "errors": []
    }
    
    # Collect top keywords from each category
    sample_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        sample_keywords.extend(keywords[:2])  # Top 2 from each category
    
    logger.info(f"Starting SERP AIO collection for {len(sample_keywords)} keywords")
    
    for keyword in sample_keywords:
        try:
            logger.info(f"Collecting SERP AIO for keyword: {keyword}")
            
            if dry_run:
                logger.info(f"[DRY RUN] Would query SerpAPI for '{keyword}'")
                stats["queries_processed"] += 1
                continue
            
            params = {
                "q": keyword,
                "api_key": serpapi_key,
                "engine": "google",
                "hl": "en",
                "gl": "us"
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check for AI Overview
            aio_data = {}
            if "ai_overview" in results:
                aio_data = {
                    "aio_text": results["ai_overview"].get("text", ""),
                    "cited_sources": results["ai_overview"].get("cited_sources", []),
                    "locale": "en-US"
                }
                upsert_serp_aio(keyword, aio_data, run_id)
                stats["aio_found"] += 1
                logger.info(f"Found AI Overview for '{keyword}'")
            else:
                logger.info(f"No AI Overview found for '{keyword}'")
            
            stats["queries_processed"] += 1
            
            # Rate limiting
            time.sleep(1)
        
        except Exception as e:
            logger.error(f"Error collecting SERP AIO for keyword '{keyword}': {e}")
            stats["errors"].append(str(e))
    
    logger.info(f"SERP AIO collection completed: {stats['aio_found']} AIO found")
    return stats
