#!/usr/bin/env python3
"""클러스터링 데이터 확인 스크립트"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    # dotenv가 없으면 .env 파일을 직접 읽기
    import os
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and not os.getenv(key):
                        os.environ[key] = value

from web.db_queries import get_db_connection

print("=" * 60)
print("클러스터링 데이터 확인")
print("=" * 60)

# DB 연결 확인
conn = get_db_connection()
if conn is None:
    print("❌ 데이터베이스 연결 실패")
    print("\n확인 사항:")
    print("1. DATABASE_URL 환경 변수가 설정되어 있는지 확인")
    print("2. .env 파일에 DATABASE_URL이 있는지 확인")
    print("3. Railway 환경 변수가 설정되어 있는지 확인")
    sys.exit(1)

print("✅ 데이터베이스 연결 성공\n")

try:
    with conn.cursor() as cur:
        # 1. clusters 테이블 존재 확인
        print("1. 테이블 존재 확인")
        print("-" * 60)
        
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'clusters'
            )
        """)
        clusters_exists = cur.fetchone()[0]
        print(f"clusters 테이블: {'✅ 존재' if clusters_exists else '❌ 없음'}")
        
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'cluster_assignments'
            )
        """)
        assignments_exists = cur.fetchone()[0]
        print(f"cluster_assignments 테이블: {'✅ 존재' if assignments_exists else '❌ 없음'}")
        
        if not clusters_exists or not assignments_exists:
            print("\n⚠️ 필요한 테이블이 없습니다. 마이그레이션을 실행하세요.")
            sys.exit(1)
        
        print("\n2. 데이터 개수 확인")
        print("-" * 60)
        
        # clusters 테이블 데이터 개수
        cur.execute("SELECT COUNT(*) FROM clusters")
        total_clusters = cur.fetchone()[0]
        print(f"전체 clusters: {total_clusters}개")
        
        cur.execute("SELECT COUNT(*) FROM clusters WHERE noise_label = FALSE")
        valid_clusters = cur.fetchone()[0]
        print(f"유효한 clusters (noise_label=FALSE): {valid_clusters}개")
        
        # cluster_assignments 테이블 데이터 개수
        cur.execute("SELECT COUNT(*) FROM cluster_assignments")
        total_assignments = cur.fetchone()[0]
        print(f"전체 cluster_assignments: {total_assignments}개")
        
        cur.execute("SELECT COUNT(DISTINCT cluster_id) FROM cluster_assignments")
        clusters_with_assignments = cur.fetchone()[0]
        print(f"할당이 있는 클러스터 수: {clusters_with_assignments}개")
        
        print("\n3. 샘플 데이터 확인")
        print("-" * 60)
        
        if valid_clusters > 0:
            # 최근 클러스터 샘플
            cur.execute("""
                SELECT cluster_id, topic_category, sub_cluster_index, size, 
                       created_at, created_from_run_id
                FROM clusters 
                WHERE noise_label = FALSE
                ORDER BY created_at DESC
                LIMIT 5
            """)
            samples = cur.fetchall()
            print("최근 클러스터 샘플 (최대 5개):")
            for sample in samples:
                cluster_id, topic_category, sub_cluster_index, size, created_at, run_id = sample
                print(f"  - Cluster ID: {cluster_id}, Category: {topic_category}, "
                      f"Sub Index: {sub_cluster_index}, Size: {size}, "
                      f"Created: {created_at}, Run ID: {run_id}")
            
            # 할당 데이터 샘플
            if total_assignments > 0:
                cur.execute("""
                    SELECT ca.cluster_id, ca.doc_type, ca.doc_id, ca.is_representative,
                           c.topic_category, c.sub_cluster_index
                    FROM cluster_assignments ca
                    JOIN clusters c ON ca.cluster_id = c.cluster_id
                    WHERE c.noise_label = FALSE
                    LIMIT 5
                """)
                assignment_samples = cur.fetchall()
                print("\n할당 데이터 샘플 (최대 5개):")
                for sample in assignment_samples:
                    cluster_id, doc_type, doc_id, is_rep, topic_cat, sub_idx = sample
                    rep_str = "대표" if is_rep else "일반"
                    print(f"  - Cluster {cluster_id} ({topic_cat}_{sub_idx}): "
                          f"{doc_type} {doc_id} ({rep_str})")
        else:
            print("⚠️ 유효한 클러스터 데이터가 없습니다.")
        
        print("\n4. 쿼리 테스트")
        print("-" * 60)
        
        # 실제 get_clustering_results_from_db()에서 사용하는 쿼리 실행
        cur.execute("""
            SELECT 
                c.cluster_id,
                c.size,
                c.algorithm,
                c.summary,
                c.topic_category,
                c.sub_cluster_index,
                c.top_keywords,
                CASE 
                    WHEN c.topic_category IS NOT NULL AND c.sub_cluster_index IS NOT NULL 
                    THEN c.topic_category || '_' || (c.sub_cluster_index + 1)::text
                    ELSE 'Cluster_' || c.cluster_id::text
                END as cluster_name,
                COALESCE(
                    jsonb_agg(DISTINCT ca.doc_id) FILTER (WHERE ca.doc_id IS NOT NULL),
                    '[]'::jsonb
                ) as post_ids,
                COALESCE(
                    jsonb_agg(DISTINCT ca.doc_id) FILTER (WHERE ca.is_representative = TRUE AND ca.doc_id IS NOT NULL),
                    '[]'::jsonb
                ) as representative_post_ids,
                COUNT(DISTINCT ca.doc_id) FILTER (WHERE ca.is_representative = TRUE) as representative_count
            FROM clusters c
            LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
            WHERE c.noise_label = FALSE
            GROUP BY c.cluster_id, c.size, c.algorithm, c.summary, c.topic_category, c.sub_cluster_index, c.top_keywords
            ORDER BY c.topic_category, c.sub_cluster_index, c.size DESC
            LIMIT 5
        """)
        query_results = cur.fetchall()
        print(f"쿼리 결과: {len(query_results)}개 행 반환")
        
        if len(query_results) > 0:
            print("✅ 쿼리가 정상적으로 실행되었습니다.")
            print("\n쿼리 결과 샘플:")
            for row in query_results[:3]:
                cluster_id, size, algorithm, summary, topic_cat, sub_idx, top_kw, cluster_name, post_ids, rep_ids, rep_count = row
                print(f"  - {cluster_name}: size={size}, posts={len(post_ids) if isinstance(post_ids, list) else 'N/A'}")
        else:
            print("⚠️ 쿼리 결과가 비어있습니다.")
            print("\n가능한 원인:")
            print("1. clusters 테이블에 noise_label=FALSE인 데이터가 없음")
            print("2. 데이터가 있지만 쿼리 조건에 맞지 않음")
        
        print("\n5. 파이프라인 실행 기록 확인")
        print("-" * 60)
        
        cur.execute("""
            SELECT run_id, run_type, status, created_at, metadata
            FROM pipeline_runs
            WHERE run_type LIKE '%clustering%'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        runs = cur.fetchall()
        if runs:
            print("최근 클러스터링 관련 실행 기록:")
            for run in runs:
                run_id, run_type, status, created_at, metadata = run
                print(f"  - Run ID: {run_id}, Type: {run_type}, Status: {status}, "
                      f"Created: {created_at}")
                if metadata:
                    print(f"    Metadata: {metadata}")
        else:
            print("⚠️ 클러스터링 관련 실행 기록이 없습니다.")
            print("   load_clustering_results.py를 실행하여 데이터를 적재하세요.")
        
finally:
    conn.close()
    print("\n" + "=" * 60)
    print("확인 완료")
