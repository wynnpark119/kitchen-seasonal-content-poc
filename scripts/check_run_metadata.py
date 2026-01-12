#!/usr/bin/env python3
"""
특정 run_id의 메타데이터 확인
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection

conn = None
try:
    conn = get_db_connection()
    with conn.cursor() as cur:
        # run 30의 메타데이터 확인
        cur.execute("""
            SELECT run_id, run_type, status, started_at, completed_at, error_message, metadata
            FROM pipeline_runs
            WHERE run_id = 30
        """)
        
        result = cur.fetchone()
        if result:
            run_id, run_type, status, started_at, completed_at, error_message, metadata = result
            print(f"Run {run_id}:")
            print(f"  Type: {run_type}")
            print(f"  Status: {status}")
            print(f"  Started: {started_at}")
            print(f"  Completed: {completed_at}")
            print(f"  Error: {error_message}")
            print(f"  Metadata: {json.dumps(metadata, indent=2, default=str) if metadata else 'None'}")

finally:
    if conn:
        put_db_connection(conn)
