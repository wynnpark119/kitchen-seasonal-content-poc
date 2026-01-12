#!/usr/bin/env python3
"""
데이터 적재 완료 여부 확인 스크립트

Railway Worker 서비스에서 실행하거나,
로컬에서 DATABASE_URL을 설정하여 실행 가능
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection

def verify_data_loaded():
    """데이터 적재 완료 여부 확인"""
    print("=" * 60)
    print("데이터 적재 완료 여부 확인")
    print("=" * 60)
    
    # DATABASE_URL 확인
    db_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    
    if not db_url:
        print("\n❌ DATABASE_URL이 설정되지 않았습니다.")
        print("   Railway Worker 서비스의 Variables에서 DATABASE_URL을 확인하세요.")
        return False
    
    print(f"\n✅ DATABASE_URL 설정됨")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. 총 포스트 수 확인
        cur.execute("SELECT COUNT(*) FROM raw_reddit_posts")
        total_posts = cur.fetchone()[0]
        print(f"\n📊 총 Reddit 포스트 수: {total_posts}")
        
        if total_posts == 0:
            print("   ⚠️  데이터가 없습니다. Worker가 아직 실행 중이거나 실패했을 수 있습니다.")
            return False
        
        # 2. 키워드별 포스트 수 확인 (20개 키워드 모두 확인)
        expected_keywords = [
            "spring dinner ideas",
            "easy spring meals",
            "what to cook in spring",
            "spring meal prep",
            "light spring recipes",
            "spring kitchen decor",
            "kitchen spring refresh",
            "spring table setting ideas",
            "how to decorate kitchen for spring",
            "spring kitchen ideas",
            "refrigerator organization",
            "fridge organization tips",
            "how to organize refrigerator",
            "refrigerator storage ideas",
            "fridge organization system",
            "vegetable prep",
            "how to prep vegetables",
            "vegetable storage tips",
            "how to store vegetables",
            "vegetable washing tips"
        ]
        
        cur.execute("""
            SELECT keyword, COUNT(*) as count 
            FROM raw_reddit_posts 
            GROUP BY keyword 
            ORDER BY keyword
        """)
        keyword_counts = {row[0]: row[1] for row in cur.fetchall()}
        
        print(f"\n📝 키워드별 포스트 수 (예상: 20개 키워드):")
        loaded_keywords = 0
        for keyword in expected_keywords:
            count = keyword_counts.get(keyword, 0)
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {keyword}: {count}개")
            if count > 0:
                loaded_keywords += 1
        
        print(f"\n   총 {loaded_keywords}/20개 키워드에 데이터가 있습니다.")
        
        # 3. 총 댓글 수 확인
        cur.execute("SELECT COUNT(*) FROM raw_reddit_comments")
        total_comments = cur.fetchone()[0]
        print(f"\n💬 총 Reddit 댓글 수: {total_comments}")
        
        # 4. 최근 수집된 포스트 확인
        cur.execute("""
            SELECT keyword, title, upvotes, created_at 
            FROM raw_reddit_posts 
            ORDER BY created_at DESC 
            LIMIT 3
        """)
        recent_posts = cur.fetchall()
        
        if recent_posts:
            print(f"\n🕐 최근 수집된 포스트 (상위 3개):")
            for keyword, title, upvotes, created_at in recent_posts:
                title_short = title[:60] + "..." if len(title) > 60 else title
                print(f"  - [{keyword}] {title_short}")
                print(f"    ↑{upvotes} | {created_at}")
        
        # 5. Pipeline runs 확인
        cur.execute("""
            SELECT run_id, run_type, status, started_at, completed_at, metadata
            FROM pipeline_runs 
            WHERE run_type = 'collect' OR run_type = 'save_keywords'
            ORDER BY started_at DESC 
            LIMIT 1
        """)
        latest_run = cur.fetchone()
        
        if latest_run:
            run_id, run_type, status, started_at, completed_at, metadata = latest_run
            print(f"\n🔄 최근 Pipeline Run:")
            print(f"  Run ID: {run_id}")
            print(f"  Type: {run_type}")
            print(f"  Status: {status}")
            print(f"  Started: {started_at}")
            print(f"  Completed: {completed_at}")
            if metadata:
                print(f"  Metadata: {metadata}")
        
        cur.close()
        conn.close()
        
        # 최종 판단
        print("\n" + "=" * 60)
        if total_posts > 0 and loaded_keywords >= 15:  # 15개 이상이면 충분히 적재된 것으로 간주
            print("✅ 데이터 적재 완료!")
            print(f"   - 총 {total_posts}개 포스트")
            print(f"   - 총 {total_comments}개 댓글")
            print(f"   - {loaded_keywords}개 키워드에 데이터 있음")
            return True
        elif total_posts > 0:
            print("⚠️  데이터가 일부만 적재되었습니다.")
            print(f"   - 총 {total_posts}개 포스트")
            print(f"   - {loaded_keywords}/20개 키워드에 데이터 있음")
            return False
        else:
            print("❌ 데이터 적재가 완료되지 않았습니다.")
            print("   Worker 로그를 확인하세요.")
            return False
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_data_loaded()
    sys.exit(0 if success else 1)
