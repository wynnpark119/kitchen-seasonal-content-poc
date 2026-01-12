"""
Helper script to save MCP Apify results to database
This can be called after MCP get-actor-output to save all collected data
"""
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.db import create_pipeline_run, update_pipeline_run, get_db_connection
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_mcp_results")

def save_mcp_results_to_db(dataset_id: str, keyword: str, run_id: int = None):
    """
    Save MCP Apify results to database
    
    Args:
        dataset_id: Apify dataset ID from MCP call
        keyword: Search keyword used
        run_id: Optional pipeline run ID (creates new if not provided)
    """
    if not run_id:
        run_id = create_pipeline_run('collect', 'running')
        logger.info(f"Created new pipeline run: {run_id}")
    
    logger.info(f"Processing dataset {dataset_id} for keyword '{keyword}'")
    logger.info("Note: This function requires MCP get-actor-output to fetch items")
    logger.info("Use mcp_apify_get-actor-output tool to get items, then call process_apify_results()")
    
    return run_id

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python save_mcp_results.py <dataset_id> <keyword> [run_id]")
        sys.exit(1)
    
    dataset_id = sys.argv[1]
    keyword = sys.argv[2]
    run_id = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    save_mcp_results_to_db(dataset_id, keyword, run_id)
