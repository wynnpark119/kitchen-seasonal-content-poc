#!/usr/bin/env python3
"""
클러스터링 작업 모니터링 스크립트

데이터베이스를 조회하여 클러스터링 진행 상황을 실시간으로 모니터링합니다.
"""
import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

# .env 파일 로드
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    project_root = Path(__file__).parent
    env_path = project_root / ".env"
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not os.getenv(key):
                            os.environ[key] = value
        except (PermissionError, IOError):
            pass

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.config import CATEGORIES
import psycopg2


def retry_db_query(func, max_retries=3, delay=2):
    """데이터베이스 쿼리 재시도 데코레이터"""
    for attempt in range(max_retries):
        try:
            return func()
        except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError) as e:
            if attempt < max_retries - 1:
                print(f"⚠️  데이터베이스 연결 실패 (시도 {attempt + 1}/{max_retries}), {delay}초 후 재시도...")
                time.sleep(delay)
            else:
                raise


def format_duration(seconds: float) -> str:
    """초를 읽기 쉬운 형식으로 변환"""
    if seconds < 60:
        return f"{seconds:.1f}초"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}분 {secs}초"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}시간 {minutes}분"


def get_latest_clustering_run() -> Optional[Dict[str, Any]]:
    """가장 최근 클러스터링 실행 정보 조회"""
    def _query():
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        run_id,
                        run_type,
                        status,
                        started_at,
                        completed_at,
                        error_message,
                        metadata,
                        updated_at
                    FROM pipeline_runs
                    WHERE run_type LIKE '%cluster%'
                    ORDER BY started_at DESC
                    LIMIT 1
                """)
                
                row = cur.fetchone()
                if not row:
                    return None
                
                return {
                    "run_id": row[0],
                    "run_type": row[1],
                    "status": row[2],
                    "started_at": row[3],
                    "completed_at": row[4],
                    "error_message": row[5],
                    "metadata": row[6],
                    "updated_at": row[7]
                }
        finally:
            if conn:
                put_db_connection(conn)
    
    return retry_db_query(_query)


def get_clustering_stats(run_id: Optional[int] = None) -> Dict[str, Any]:
    """클러스터링 통계 조회"""
    def _query():
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # 전체 클러스터 수
                if run_id:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM clusters 
                        WHERE created_from_run_id = %s
                    """, (run_id,))
                else:
                    cur.execute("SELECT COUNT(*) FROM clusters")
                total_clusters = cur.fetchone()[0]
                
                # 전체 할당 수
                if run_id:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM cluster_assignments 
                        WHERE created_from_run_id = %s
                    """, (run_id,))
                else:
                    cur.execute("SELECT COUNT(*) FROM cluster_assignments")
                total_assignments = cur.fetchone()[0]
                
                # 카테고리별 클러스터 수
                category_stats = {}
                for category in CATEGORIES:
                    if run_id:
                        cur.execute("""
                            SELECT COUNT(*) 
                            FROM clusters 
                            WHERE created_from_run_id = %s
                            AND params_json->>'topic_category' = %s
                        """, (run_id, category))
                    else:
                        cur.execute("""
                            SELECT COUNT(*) 
                            FROM clusters 
                            WHERE params_json->>'topic_category' = %s
                        """, (category,))
                    count = cur.fetchone()[0]
                    category_stats[category] = count
                
                # 카테고리별 할당 수
                category_assignments = {}
                for category in CATEGORIES:
                    if run_id:
                        cur.execute("""
                            SELECT COUNT(*) 
                            FROM cluster_assignments ca
                            JOIN clusters c ON ca.cluster_id = c.cluster_id
                            WHERE ca.created_from_run_id = %s
                            AND c.params_json->>'topic_category' = %s
                        """, (run_id, category))
                    else:
                        cur.execute("""
                            SELECT COUNT(*) 
                            FROM cluster_assignments ca
                            JOIN clusters c ON ca.cluster_id = c.cluster_id
                            WHERE c.params_json->>'topic_category' = %s
                        """, (category,))
                    count = cur.fetchone()[0]
                    category_assignments[category] = count
                
                # 전체 포스트 수 (클러스터링 대상)
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM raw_reddit_posts
                    WHERE title IS NOT NULL
                    AND LENGTH(COALESCE(title, '')) > 0
                """)
                total_posts = cur.fetchone()[0]
                
                return {
                    "total_clusters": total_clusters,
                    "total_assignments": total_assignments,
                    "total_posts": total_posts,
                    "category_clusters": category_stats,
                    "category_assignments": category_assignments
                }
        finally:
            if conn:
                put_db_connection(conn)
    
    return retry_db_query(_query)


def get_recent_runs(limit: int = 5) -> list:
    """최근 클러스터링 실행 목록 조회"""
    def _query():
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        run_id,
                        run_type,
                        status,
                        started_at,
                        completed_at,
                        error_message
                    FROM pipeline_runs
                    WHERE run_type LIKE '%cluster%'
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (limit,))
                
                runs = []
                rows = cur.fetchall()
                for row in rows:
                    if len(row) < 6:
                        continue  # 데이터가 부족한 경우 스킵
                    
                    duration = None
                    if row[4] and row[3]:  # completed_at과 started_at이 모두 있는 경우
                        try:
                            duration = (row[4] - row[3]).total_seconds()
                        except:
                            pass
                    
                    runs.append({
                        "run_id": row[0],
                        "run_type": row[1] if len(row) > 1 else "unknown",
                        "status": row[2] if len(row) > 2 else "unknown",
                        "started_at": row[3] if len(row) > 3 else None,
                        "completed_at": row[4] if len(row) > 4 else None,
                        "error_message": row[5] if len(row) > 5 else None,
                        "duration": duration
                    })
                
                return runs
        finally:
            if conn:
                put_db_connection(conn)
    
    try:
        return retry_db_query(_query)
    except Exception as e:
        # 에러 발생 시 빈 리스트 반환
        print(f"⚠️  최근 실행 목록 조회 실패: {e}")
        return []


def print_monitoring_dashboard(run_info: Optional[Dict], stats: Dict, watch_mode: bool = False):
    """모니터링 대시보드 출력"""
    # 화면 클리어
    if watch_mode:
        os.system('clear' if os.name != 'nt' else 'cls')
    
    print("=" * 80)
    print("🔍 클러스터링 작업 모니터링")
    print("=" * 80)
    print(f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 최근 실행 정보
    if run_info:
        print("📊 최근 클러스터링 실행 정보")
        print("-" * 80)
        print(f"  Run ID: {run_info['run_id']}")
        print(f"  실행 타입: {run_info['run_type']}")
        print(f"  상태: {run_info['status']}")
        print(f"  시작 시간: {run_info['started_at']}")
        
        if run_info['status'] == 'running':
            elapsed = (datetime.now(run_info['started_at'].tzinfo) - run_info['started_at']).total_seconds()
            print(f"  경과 시간: {format_duration(elapsed)} (진행 중...)")
        elif run_info['completed_at']:
            duration = (run_info['completed_at'] - run_info['started_at']).total_seconds()
            print(f"  완료 시간: {run_info['completed_at']}")
            print(f"  소요 시간: {format_duration(duration)}")
        
        if run_info['error_message']:
            print(f"  ⚠️  에러: {run_info['error_message']}")
        
        if run_info['metadata']:
            metadata = run_info['metadata']
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    pass
            
            if isinstance(metadata, dict):
                print(f"  처리된 포스트: {metadata.get('posts_processed', 'N/A')}")
                print(f"  생성된 클러스터: {metadata.get('clusters_created', 'N/A')}")
                print(f"  생성된 할당: {metadata.get('assignments_created', 'N/A')}")
        
        print()
    else:
        print("⚠️  클러스터링 실행 기록이 없습니다.")
        print()
    
    # 전체 통계
    print("📈 전체 통계")
    print("-" * 80)
    print(f"  전체 포스트 수: {stats['total_posts']:,}")
    print(f"  생성된 클러스터 수: {stats['total_clusters']:,}")
    print(f"  할당된 포스트 수: {stats['total_assignments']:,}")
    
    if stats['total_posts'] > 0:
        coverage = (stats['total_assignments'] / stats['total_posts']) * 100
        print(f"  클러스터링 커버리지: {coverage:.1f}%")
    
    print()
    
    # 카테고리별 통계
    print("📂 카테고리별 상세 통계")
    print("-" * 80)
    for category in CATEGORIES:
        clusters = stats['category_clusters'].get(category, 0)
        assignments = stats['category_assignments'].get(category, 0)
        print(f"  {category}:")
        print(f"    - 클러스터 수: {clusters}")
        print(f"    - 할당된 포스트 수: {assignments}")
    
    print()
    
    # 최근 실행 목록
    print("📋 최근 실행 목록 (최대 5개)")
    print("-" * 80)
    try:
        recent_runs = get_recent_runs(5)
        if recent_runs:
            for run in recent_runs:
                status_icon = "✅" if run['status'] == 'completed' else "⏳" if run['status'] == 'running' else "❌"
                duration_str = format_duration(run['duration']) if run.get('duration') else "진행 중"
                started_at = run.get('started_at') or "알 수 없음"
                print(f"  {status_icon} Run {run.get('run_id', 'N/A')}: {run.get('status', 'unknown')} ({duration_str}) - {started_at}")
        else:
            print("  실행 기록이 없습니다.")
    except Exception as e:
        print(f"  ⚠️  실행 목록 조회 실패: {e}")
    
    print("=" * 80)
    
    if watch_mode:
        print("\n💡 Ctrl+C를 눌러 종료하세요. (자동 새로고침: 5초마다)")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="클러스터링 작업 모니터링")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="실시간 모니터링 모드 (5초마다 자동 새로고침)"
    )
    parser.add_argument(
        "--run-id",
        type=int,
        help="특정 run_id의 통계만 조회"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="watch 모드에서 새로고침 간격 (초, 기본값: 5)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.watch:
            print("실시간 모니터링 모드를 시작합니다...")
            print(f"새로고침 간격: {args.interval}초")
            print("Ctrl+C를 눌러 종료하세요.\n")
            
            while True:
                run_info = get_latest_clustering_run()
                stats = get_clustering_stats(args.run_id)
                print_monitoring_dashboard(run_info, stats, watch_mode=True)
                time.sleep(args.interval)
        else:
            run_info = get_latest_clustering_run()
            stats = get_clustering_stats(args.run_id)
            print_monitoring_dashboard(run_info, stats, watch_mode=False)
    
    except KeyboardInterrupt:
        print("\n\n모니터링을 종료합니다.")
        sys.exit(0)
    except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError) as e:
        print("\n" + "=" * 80)
        print("❌ 데이터베이스 연결 실패")
        print("=" * 80)
        print(f"에러: {e}")
        print("\n가능한 원인:")
        print("  1. 데이터베이스 서버가 다운되었거나 접근할 수 없습니다")
        print("  2. 네트워크 연결 문제")
        print("  3. DATABASE_URL 환경 변수가 올바르지 않습니다")
        print("\n해결 방법:")
        print("  - DATABASE_URL 환경 변수를 확인하세요")
        print("  - 데이터베이스 서버 상태를 확인하세요")
        print("  - 잠시 후 다시 시도하세요")
        print("=" * 80)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
