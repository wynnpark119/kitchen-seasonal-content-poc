#!/usr/bin/env python3
"""
데이터베이스에 저장된 Reddit 게시물 제목 출력
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from common.db import engine
from common.config import DATABASE_URL

def print_reddit_titles(limit: int = None):
    """Reddit 게시물 제목 출력"""
    if not DATABASE_URL:
        print("❌ DATABASE_URL이 설정되지 않았습니다.")
        return
    
    try:
        # SQLAlchemy engine에서 raw connection 가져오기
        conn = engine.raw_connection()
        
        with conn.cursor() as cur:
            if limit:
                query = """
                    SELECT title
                    FROM raw_reddit_posts
                    ORDER BY created_utc DESC
                    LIMIT %s
                """
                cur.execute(query, (limit,))
            else:
                query = """
                    SELECT title
                    FROM raw_reddit_posts
                    ORDER BY created_utc DESC
                """
                cur.execute(query)
            
            results = cur.fetchall()
            
            print(f"\n📋 총 {len(results)}개의 Reddit 게시물 제목:\n")
            print("=" * 80)
            
            for idx, (title,) in enumerate(results, 1):
                if title:
                    print(f"{idx}. {title}")
                else:
                    print(f"{idx}. (제목 없음)")
            
            print("=" * 80)
            print(f"\n✅ 총 {len(results)}개 제목 출력 완료\n")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reddit 게시물 제목 출력")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="출력할 제목 개수 제한 (기본값: 전체)"
    )
    
    args = parser.parse_args()
    print_reddit_titles(limit=args.limit)
