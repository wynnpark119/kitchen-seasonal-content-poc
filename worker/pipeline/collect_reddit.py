"""
Reddit data collection via Apify MCP

Note: Apify is connected via MCP. This module processes MCP results and saves to database.
Actual MCP calls are made by the AI assistant using mcp_apify_call-actor tool.
"""
import os
import time
import json
from typing import List, Dict, Any, Optional
from .config import MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST, REDDIT_KEYWORDS
from .db import upsert_reddit_post, upsert_reddit_comment
from .logging import setup_logger
from .process_apify_results import process_apify_results

logger = setup_logger("collect_reddit")

def collect_reddit_data(run_id: int, dry_run: bool = False, mcp_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Collect Reddit posts and comments via Apify MCP
    
    Args:
        run_id: Pipeline run ID
        dry_run: If True, skip actual collection
        mcp_results: Optional dict with 'dataset_id' and 'items' from MCP call
    
    Note: MCP calls should be made by AI assistant using mcp_apify_call-actor tool.
    Apify Actor supports parallel collection by passing multiple keywords in searchTerms array.
    Results can be passed via mcp_results parameter or fetched using mcp_apify_get-actor-output.
    """
    
    stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }
    
    # Collect from all categories
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        all_keywords.extend(keywords)
    
    logger.info(f"Starting Reddit collection for {len(all_keywords)} keywords")
    
    # If mcp_results provided, process them directly
    if mcp_results:
        # Handle both single keyword and multiple keywords results
        keywords = mcp_results.get('keywords', [])
        if not keywords:
            # Fallback to single keyword for backward compatibility
            keyword = mcp_results.get('keyword', 'unknown')
            keywords = [keyword]
        
        items = mcp_results.get('items', [])
        logger.info(f"Processing {len(items)} items from MCP results for {len(keywords)} keywords")
        
        # Process items and assign keywords based on search term matching
        # Since Apify returns items with search terms, we need to match them
        try:
            # Group items by keyword if possible, otherwise process all together
            for keyword in keywords:
                # Filter items that match this keyword (if keyword info is available in items)
                # For now, process all items and assign the first keyword
                # In practice, Apify may return items with search term info
                result_stats = process_apify_results(items, keyword, run_id)
                stats["posts_collected"] += result_stats["posts_collected"]
                stats["comments_collected"] += result_stats["comments_collected"]
                stats["keywords_processed"] += 1
                if result_stats["errors"]:
                    stats["errors"].extend(result_stats["errors"])
        except Exception as e:
            logger.error(f"Error processing MCP results: {e}")
            stats["errors"].append(str(e))
        
        logger.info(f"Reddit collection completed: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
        return stats
    
    # Otherwise, prepare for parallel collection via MCP
    if dry_run:
        logger.info(f"[DRY RUN] Would collect up to {MAX_POSTS_PER_KEYWORD} posts per keyword")
        logger.info(f"[DRY RUN] Total keywords: {len(all_keywords)}")
        stats["keywords_processed"] = len(all_keywords)
        return stats
    
    # Log instructions for parallel collection
    logger.info("=" * 60)
    logger.info("PARALLEL COLLECTION MODE")
    logger.info("=" * 60)
    logger.info(f"Apify Actor supports parallel collection by passing all keywords in searchTerms array.")
    logger.info(f"Total keywords to collect: {len(all_keywords)}")
    logger.info(f"\nMCP call should be made with:")
    logger.info(f"  searchTerms: {all_keywords}")
    logger.info(f"  maxPostsCount: {MAX_POSTS_PER_KEYWORD}")
    logger.info(f"  crawlCommentsPerPost: true")
    logger.info(f"  maxCommentsPerPost: {TOP_COMMENTS_PER_POST}")
    logger.info(f"  fastMode: true")
    logger.info(f"\nExample MCP call:")
    logger.info(f"  mcp_apify_call-actor(")
    logger.info(f"    actor='harshmaur/reddit-scraper',")
    logger.info(f"    step='call',")
    logger.info(f"    input={{")
    logger.info(f"      'searchTerms': {all_keywords},")
    logger.info(f"      'searchPosts': True,")
    logger.info(f"      'searchComments': False,")
    logger.info(f"      'crawlCommentsPerPost': True,")
    logger.info(f"      'maxPostsCount': {MAX_POSTS_PER_KEYWORD},")
    logger.info(f"      'maxCommentsPerPost': {TOP_COMMENTS_PER_POST},")
    logger.info(f"      'fastMode': True,")
    logger.info(f"      'searchSort': 'hot',")
    logger.info(f"      'searchTime': 'all',")
    logger.info(f"      'includeNSFW': False,")
    logger.info(f"      'proxy': {{'useApifyProxy': True, 'apifyProxyGroups': ['RESIDENTIAL']}}")
    logger.info(f"    }}")
    logger.info(f"  )")
    logger.info("=" * 60)
    
    stats["keywords_processed"] = len(all_keywords)
    return stats
