#!/usr/bin/env python3
"""빠른 subreddit 분포 확인"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection

conn = None
try:
    conn = get_db_connection()
    with conn.cursor() as cur:
        # 모든 subreddit 목록
        cur.execute("""
            SELECT subreddit, COUNT(*) as count
            FROM raw_reddit_posts
            WHERE title IS NOT NULL
            GROUP BY subreddit
            ORDER BY count DESC
        """)
        
        subreddits = cur.fetchall()
        print(f"전체 subreddit 수: {len(subreddits)}\n")
        print("상위 30개 subreddit:")
        for subreddit, count in subreddits[:30]:
            print(f"  r/{subreddit}: {count}개")
finally:
    if conn:
        put_db_connection(conn)
