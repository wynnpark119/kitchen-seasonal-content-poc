#!/usr/bin/env python3
"""
데이터베이스에 저장된 Reddit 데이터 확인 스크립트
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection

def check_database_data():
    """데이터베이스에 저장된 데이터 확인"""
    # DATABASE_URL 확인
    db_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    
    if not db_url:
        print("❌ DATABASE_URL이 설정되지 않았습니다.")
        print("   Railway Worker 서비스의 Variables에서 DATABASE_URL을 확인하세요.")
        return
    
    print(f"✅ DATABASE_URL 설정됨: {db_url[:50]}...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 총 포스트 수 확인
        cur.execute("SELECT COUNT(*) FROM raw_reddit_posts")
        total_posts = cur.fetchone()[0]
        print(f"\n📊 총 Reddit 포스트 수: {total_posts}")
        
        # 키워드별 포스트 수
        cur.execute("""
            SELECT keyword, COUNT(*) as count 
            FROM raw_reddit_posts 
            GROUP BY keyword 
            ORDER BY count DESC
        """)
        keyword_counts = cur.fetchall()
        
        if keyword_counts:
            print("\n📝 키워드별 포스트 수:")
            for keyword, count in keyword_counts:
                print(f"  - {keyword}: {count}개")
        else:
            print("\n⚠️  키워드별 데이터가 없습니다.")
        
        # 총 댓글 수 확인
        cur.execute("SELECT COUNT(*) FROM raw_reddit_comments")
        total_comments = cur.fetchone()[0]
        print(f"\n💬 총 Reddit 댓글 수: {total_comments}")
        
        # 최근 수집된 포스트 확인
        cur.execute("""
            SELECT keyword, title, upvotes, created_at 
            FROM raw_reddit_posts 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_posts = cur.fetchall()
        
        if recent_posts:
            print("\n🕐 최근 수집된 포스트 (상위 5개):")
            for keyword, title, upvotes, created_at in recent_posts:
                title_short = title[:50] + "..." if len(title) > 50 else title
                print(f"  - [{keyword}] {title_short} (↑{upvotes}, {created_at})")
        else:
            print("\n⚠️  최근 포스트가 없습니다.")
        
        # Pipeline runs 확인
        cur.execute("""
            SELECT run_id, run_type, status, started_at, completed_at 
            FROM pipeline_runs 
            ORDER BY started_at DESC 
            LIMIT 5
        """)
        runs = cur.fetchall()
        
        if runs:
            print("\n🔄 최근 Pipeline Runs:")
            for run_id, run_type, status, started_at, completed_at in runs:
                print(f"  - Run {run_id}: {run_type} - {status} (시작: {started_at})")
        else:
            print("\n⚠️  Pipeline runs가 없습니다.")
        
        cur.close()
        conn.close()
        
        print("\n✅ 데이터베이스 확인 완료")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_data()
