"""
Google Search Console CSV ingestion
"""
import csv
import os
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from .db import upsert_gsc_query
from .logging import setup_logger

logger = setup_logger("ingest_gsc")

def ingest_gsc_csv(csv_path: str, run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Ingest GSC CSV file"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"GSC CSV file not found: {csv_path}")
    
    stats = {
        "rows_processed": 0,
        "rows_inserted": 0,
        "errors": []
    }
    
    logger.info(f"Starting GSC CSV ingestion from: {csv_path}")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    stats["rows_processed"] += 1
                    
                    if dry_run:
                        if stats["rows_processed"] <= 5:
                            logger.info(f"[DRY RUN] Sample row: {row}")
                        continue
                    
                    # Validate required fields
                    required_fields = ['query', 'date', 'impressions', 'clicks']
                    if not all(field in row for field in required_fields):
                        logger.warning(f"Row {stats['rows_processed']} missing required fields, skipping")
                        continue
                    
                    # Validate date range (last year: Jan 1 - Dec 31)
                    try:
                        date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                        current_year = datetime.now().year
                        if date_obj.year != current_year - 1:
                            logger.debug(f"Row date {row['date']} not in last year, skipping")
                            continue
                    except ValueError:
                        logger.warning(f"Invalid date format: {row['date']}, skipping")
                        continue
                    
                    upsert_gsc_query(row, run_id)
                    stats["rows_inserted"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing row {stats['rows_processed']}: {e}")
                    stats["errors"].append(str(e))
    
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise
    
    logger.info(f"GSC CSV ingestion completed: {stats['rows_inserted']} rows inserted")
    return stats
