#!/usr/bin/env python3
"""
Save MCP Apify dataset results to database

Usage:
    python worker/scripts/save_mcp_dataset.py <dataset_id> <keyword> [run_id]

Example:
    python worker/scripts/save_mcp_dataset.py h18IWL9992IVoiwD1 "spring dinner ideas" 5
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_mcp_dataset")

def save_dataset_from_mcp(dataset_id: str, keyword: str, run_id: int = None):
    """
    Save MCP Apify dataset to database
    
    Note: This script requires MCP get-actor-output to fetch items first.
    The items should be passed as JSON or fetched using mcp_apify_get-actor-output.
    """
    if not run_id:
        run_id = create_pipeline_run('collect', 'running')
        logger.info(f"Created new pipeline run: {run_id}")
    else:
        logger.info(f"Using existing pipeline run: {run_id}")
    
    logger.info(f"Processing dataset {dataset_id} for keyword '{keyword}'")
    logger.info("Note: Use mcp_apify_get-actor-output to fetch items, then process them")
    
    return run_id

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python save_mcp_dataset.py <dataset_id> <keyword> [run_id]")
        print("\nExample:")
        print('  python save_mcp_dataset.py h18IWL9992IVoiwD1 "spring dinner ideas" 5')
        sys.exit(1)
    
    dataset_id = sys.argv[1]
    keyword = sys.argv[2]
    run_id = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    save_dataset_from_mcp(dataset_id, keyword, run_id)
    print(f"\nTo process items:")
    print(f"1. Use mcp_apify_get-actor-output with datasetId='{dataset_id}'")
    print(f"2. Call process_apify_results(items, '{keyword}', {run_id or 'new_run_id'})")
