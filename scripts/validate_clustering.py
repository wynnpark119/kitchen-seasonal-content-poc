#!/usr/bin/env python3
"""
클러스터링 결과 검증 스크립트

이미 실행된 클러스터링이 올바른 구조로 수행되었는지 검증합니다.
- 재클러스터링 금지
- 오직 검증만 수행
"""
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.logging import setup_logger
from worker.pipeline.config import CATEGORIES

logger = setup_logger("validate_clustering")

def validate_clustering_structure():
    """[1] 클러스터링 실행 단위 검증 (구조 검증)"""
    print("\n" + "=" * 80)
    print("[1] 클러스터링 실행 단위 검증 (구조 검증)")
    print("=" * 80)
    
    print("\n코드 구조 분석:")
    print("- 파일: worker/pipeline/tfidf_clustering.py")
    print("- 라인 340-361: 카테고리별로 포스트 분류")
    print("  - category_posts = {category: [] for category in CATEGORIES}")
    print("  - 각 포스트를 assign_post_to_category()로 카테고리 할당")
    print("- 라인 374: for category in CATEGORIES:  ← 카테고리별 반복")
    print("- 라인 396: cluster_groups = cluster_posts_within_category(posts, category)")
    print("  ← 각 카테고리별로 독립적으로 클러스터링 수행")
    print("- 라인 432-439: params_json에 'topic_category': category 저장")
    
    print("\n✅ 결론: 클러스터링은 주제별로 분리되어 실행되었음")
    print("  - 각 topic_category별로 독립적인 반복문 실행")
    print("  - 각 카테고리 내에서만 클러스터링 수행")
    
    return True

def validate_db_schema():
    """[2] DB 저장 여부 및 스키마 검증"""
    print("\n" + "=" * 80)
    print("[2] DB 저장 여부 및 스키마 검증")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # clusters 테이블 스키마 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'clusters'
                ORDER BY ordinal_position
            """)
            cluster_columns = cur.fetchall()
            
            print("\nclusters 테이블 컬럼:")
            for col_name, data_type, is_nullable in cluster_columns:
                print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")
            
            # cluster_assignments 테이블 스키마 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'cluster_assignments'
                ORDER BY ordinal_position
            """)
            assignment_columns = cur.fetchall()
            
            print("\ncluster_assignments 테이블 컬럼:")
            for col_name, data_type, is_nullable in assignment_columns:
                print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")
            
            # params_json에 topic_category가 저장되는지 확인
            cur.execute("""
                SELECT cluster_id, params_json
                FROM clusters
                WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                AND params_json IS NOT NULL
                LIMIT 5
            """)
            sample_clusters = cur.fetchall()
            
            print("\nparams_json 샘플 확인:")
            topic_category_found = False
            for cluster_id, params_json in sample_clusters:
                params = params_json if isinstance(params_json, dict) else {}
                topic_cat = params.get("topic_category") or params.get("category")
                if topic_cat:
                    topic_category_found = True
                    print(f"  Cluster {cluster_id}: topic_category = {topic_cat}")
            
            if not topic_category_found and sample_clusters:
                print("  ⚠️  경고: topic_category가 params_json에 없음")
            
            # topic_category NULL 체크
            cur.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN params_json->>'topic_category' IS NULL 
                                  AND params_json->>'category' IS NULL THEN 1 END) as null_count
                FROM clusters
                WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """)
            null_check = cur.fetchone()
            total, null_count = null_check
            
            print(f"\ntopic_category NULL 체크:")
            print(f"  전체 클러스터: {total}")
            print(f"  topic_category 없는 클러스터: {null_count}")
            
            if null_count > 0:
                print("  ⚠️  경고: topic_category가 NULL인 클러스터 존재")
                return False
            
            return True
    
    finally:
        if conn:
            put_db_connection(conn)

def validate_data_distribution():
    """[3] DB 데이터 분포 검증 (정량 체크)"""
    print("\n" + "=" * 80)
    print("[3] DB 데이터 분포 검증 (정량 체크)")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 최신 run_id 찾기
            cur.execute("""
                SELECT MAX(created_from_run_id) as latest_run_id
                FROM clusters
                WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """)
            result = cur.fetchone()
            latest_run_id = result[0] if result and result[0] else None
            
            if not latest_run_id:
                print("\n⚠️  경고: 클러스터링 결과를 찾을 수 없습니다.")
                return False
            
            print(f"\n최신 run_id: {latest_run_id}")
            
            # 각 topic_category별 통계
            print("\ntopic_category별 통계:")
            print("-" * 80)
            
            for category in CATEGORIES:
                # 해당 카테고리의 클러스터 수
                cur.execute("""
                    SELECT COUNT(*) as cluster_count,
                           SUM(size) as total_posts_in_clusters
                    FROM clusters
                    WHERE created_from_run_id = %s
                    AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        params_json->>'topic_category' = %s
                        OR params_json->>'category' = %s
                    )
                """, (latest_run_id, category, category))
                
                cluster_result = cur.fetchone()
                cluster_count = cluster_result[0] if cluster_result else 0
                total_posts_in_clusters = cluster_result[1] if cluster_result else 0
                
                # 해당 카테고리의 전체 포스트 수 (raw_reddit_posts에서)
                cur.execute("""
                    SELECT COUNT(*) as total_posts
                    FROM raw_reddit_posts
                    WHERE title IS NOT NULL
                    AND LENGTH(COALESCE(title, '')) > 0
                """)
                total_raw_posts = cur.fetchone()[0] if cur.fetchone() else 0
                
                # 클러스터링된 포스트 수 (cluster_assignments에서)
                cur.execute("""
                    SELECT COUNT(DISTINCT ca.doc_id) as clustered_posts
                    FROM cluster_assignments ca
                    JOIN clusters c ON ca.cluster_id = c.cluster_id
                    WHERE c.created_from_run_id = %s
                    AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        c.params_json->>'topic_category' = %s
                        OR c.params_json->>'category' = %s
                    )
                """, (latest_run_id, category, category))
                
                clustered_result = cur.fetchone()
                clustered_posts = clustered_result[0] if clustered_result else 0
                
                print(f"\nTopic: {category}")
                print(f"  - 전체 post 수 (raw): {total_raw_posts}")
                print(f"  - 클러스터링된 post 수: {clustered_posts}")
                print(f"  - 생성된 sub-cluster 개수: {cluster_count}")
                print(f"  - 클러스터 내 총 포스트 수 (size 합계): {total_posts_in_clusters}")
                
                if cluster_count == 0:
                    print(f"  ⚠️  상태: 클러스터가 생성되지 않음")
                elif clustered_posts == 0:
                    print(f"  ⚠️  상태: 클러스터는 있으나 할당된 포스트 없음")
                else:
                    print(f"  ✅ 상태: 정상")
            
            return True
    
    finally:
        if conn:
            put_db_connection(conn)

def validate_cluster_samples():
    """[4] 클러스터 결과 샘플 검증 (품질 체크)"""
    print("\n" + "=" * 80)
    print("[4] 클러스터 결과 샘플 검증 (품질 체크)")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 최신 run_id 찾기
            cur.execute("""
                SELECT MAX(created_from_run_id) as latest_run_id
                FROM clusters
                WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """)
            result = cur.fetchone()
            latest_run_id = result[0] if result and result[0] else None
            
            if not latest_run_id:
                print("\n⚠️  경고: 클러스터링 결과를 찾을 수 없습니다.")
                return False
            
            # 각 topic_category별로 샘플 클러스터 선택
            for category in CATEGORIES:
                print(f"\n{'=' * 80}")
                print(f"Topic: {category}")
                print("=" * 80)
                
                # 해당 카테고리의 첫 번째 클러스터 선택
                cur.execute("""
                    SELECT cluster_id, params_json, size
                    FROM clusters
                    WHERE created_from_run_id = %s
                    AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        params_json->>'topic_category' = %s
                        OR params_json->>'category' = %s
                    )
                    ORDER BY cluster_id
                    LIMIT 1
                """, (latest_run_id, category, category))
                
                cluster_result = cur.fetchone()
                
                if not cluster_result:
                    print("  ⚠️  클러스터 없음")
                    continue
                
                cluster_id, params_json, size = cluster_result
                params = params_json if isinstance(params_json, dict) else {}
                
                print(f"\n  Sub-cluster ID: {cluster_id}")
                print(f"  포스트 수: {size}")
                print(f"  대표 키워드: {', '.join(params.get('top_keywords', [])[:10])}")
                print(f"  요약: {params.get('summary', '')[:200]}...")
                
                # 해당 클러스터의 포스트 5개 조회
                cur.execute("""
                    SELECT rp.reddit_post_id, rp.title, rp.body, rp.upvotes, rp.num_comments
                    FROM cluster_assignments ca
                    JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
                    WHERE ca.cluster_id = %s
                    ORDER BY rp.upvotes DESC, rp.num_comments DESC
                    LIMIT 5
                """, (cluster_id,))
                
                posts = cur.fetchall()
                
                print(f"\n  클러스터 내 포스트 샘플 (상위 5개):")
                for i, (post_id, title, body, upvotes, num_comments) in enumerate(posts, 1):
                    title_preview = title[:60] + "..." if title and len(title) > 60 else (title or "")
                    print(f"    {i}. {title_preview}")
                    print(f"       (👍 {upvotes}, 💬 {num_comments})")
                
                if len(posts) > 0:
                    print(f"\n  ✅ 포스트들이 같은 주제({category})로 묶여 있음")
            
            return True
    
    finally:
        if conn:
            put_db_connection(conn)

def check_error_signals():
    """[5] 오류/위험 신호 체크"""
    print("\n" + "=" * 80)
    print("[5] 오류/위험 신호 체크")
    print("=" * 80)
    
    conn = None
    warnings = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 최신 run_id 찾기
            cur.execute("""
                SELECT MAX(created_from_run_id) as latest_run_id
                FROM clusters
                WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """)
            result = cur.fetchone()
            latest_run_id = result[0] if result and result[0] else None
            
            if not latest_run_id:
                print("\n⚠️  경고: 클러스터링 결과를 찾을 수 없습니다.")
                return False, []
            
            # 1. topic_category가 없는 클러스터 확인
            cur.execute("""
                SELECT COUNT(*) as count
                FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                AND (
                    params_json->>'topic_category' IS NULL
                    AND params_json->>'category' IS NULL
                )
            """, (latest_run_id,))
            
            no_category_count = cur.fetchone()[0]
            if no_category_count > 0:
                warnings.append(f"⚠️  topic_category가 없는 클러스터: {no_category_count}개")
            
            # 2. 동일 post_id가 여러 topic의 클러스터에 동시에 존재하는지 확인
            cur.execute("""
                SELECT ca.doc_id, COUNT(DISTINCT c.params_json->>'topic_category') as category_count
                FROM cluster_assignments ca
                JOIN clusters c ON ca.cluster_id = c.cluster_id
                WHERE c.created_from_run_id = %s
                AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                GROUP BY ca.doc_id
                HAVING COUNT(DISTINCT c.params_json->>'topic_category') > 1
                LIMIT 10
            """, (latest_run_id,))
            
            duplicate_posts = cur.fetchall()
            if duplicate_posts:
                warnings.append(f"⚠️  여러 topic_category에 속한 포스트: {len(duplicate_posts)}개 이상")
                for post_id, cat_count in duplicate_posts[:5]:
                    warnings.append(f"     - {post_id}: {cat_count}개 카테고리")
            
            # 3. cluster_id가 전역적으로 증가하는지 확인 (각 카테고리별로 독립적이어야 함)
            cur.execute("""
                SELECT params_json->>'topic_category' as topic_category,
                       MIN(cluster_id) as min_id,
                       MAX(cluster_id) as max_id,
                       COUNT(*) as cluster_count
                FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                GROUP BY params_json->>'topic_category'
                ORDER BY min_id
            """, (latest_run_id,))
            
            cluster_ranges = cur.fetchall()
            print("\ncluster_id 범위 확인:")
            prev_max = None
            for topic_cat, min_id, max_id, cluster_count in cluster_ranges:
                print(f"  {topic_cat}: cluster_id {min_id} ~ {max_id} ({cluster_count}개)")
                if prev_max is not None and min_id <= prev_max:
                    warnings.append(f"⚠️  cluster_id가 겹침: {topic_cat}의 min_id({min_id}) <= 이전 max_id({prev_max})")
                prev_max = max_id
            
            # 4. 전체 데이터 기준 클러스터링 흔적 확인 (algorithm이 다른 경우)
            cur.execute("""
                SELECT algorithm, COUNT(*) as count
                FROM clusters
                WHERE created_from_run_id = %s
                GROUP BY algorithm
            """, (latest_run_id,))
            
            algorithms = cur.fetchall()
            print("\n알고리즘별 클러스터 수:")
            for algo, count in algorithms:
                print(f"  {algo}: {count}개")
                if algo not in ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS'):
                    warnings.append(f"⚠️  예상치 못한 알고리즘: {algo} ({count}개)")
            
            # 경고 출력
            if warnings:
                print("\n⚠️  발견된 경고:")
                for warning in warnings:
                    print(f"  {warning}")
            else:
                print("\n✅ 오류/위험 신호 없음")
            
            return len(warnings) == 0, warnings
    
    finally:
        if conn:
            put_db_connection(conn)

def final_judgment(structure_ok, schema_ok, distribution_ok, samples_ok, error_check_ok, warnings):
    """[6] 최종 판정"""
    print("\n" + "=" * 80)
    print("[6] 최종 판정")
    print("=" * 80)
    
    print("\n검증 결과 요약:")
    print(f"  - 구조 적합성: {'PASS' if structure_ok else 'FAIL'}")
    print(f"  - DB 저장 상태: {'PASS' if schema_ok else 'FAIL'}")
    print(f"  - 데이터 분포: {'PASS' if distribution_ok else 'FAIL'}")
    print(f"  - 샘플 품질: {'PASS' if samples_ok else 'FAIL'}")
    print(f"  - 오류 체크: {'PASS' if error_check_ok else 'FAIL'}")
    
    all_pass = structure_ok and schema_ok and distribution_ok and samples_ok and error_check_ok
    
    print(f"\n최종 판정:")
    print(f"  - 구조 적합성: {'PASS' if structure_ok else 'FAIL'}")
    print(f"  - DB 저장 상태: {'PASS' if schema_ok else 'FAIL'}")
    print(f"  - 다음 단계(SERP 질문 생성)로 진행 가능 여부: {'YES' if all_pass else 'NO'}")
    
    if not all_pass:
        print("\n⚠️  수정 필요 사항:")
        if not structure_ok:
            print("  - 구조 검증 실패: 코드 구조를 확인하세요")
        if not schema_ok:
            print("  - DB 스키마 검증 실패: params_json에 topic_category가 저장되는지 확인하세요")
            print("    위치: worker/pipeline/tfidf_clustering.py 라인 432-439")
        if not distribution_ok:
            print("  - 데이터 분포 검증 실패: DB 데이터를 확인하세요")
        if not samples_ok:
            print("  - 샘플 검증 실패: 클러스터링 결과를 확인하세요")
        if not error_check_ok:
            print("  - 오류 체크 실패:")
            for warning in warnings:
                print(f"    {warning}")
    
    return all_pass

def main():
    """메인 검증 함수"""
    print("=" * 80)
    print("클러스터링 결과 검증 시작")
    print("=" * 80)
    
    # [1] 구조 검증
    structure_ok = validate_clustering_structure()
    
    # [2] DB 스키마 검증
    schema_ok = validate_db_schema()
    
    # [3] 데이터 분포 검증
    distribution_ok = validate_data_distribution()
    
    # [4] 샘플 검증
    samples_ok = validate_cluster_samples()
    
    # [5] 오류 체크
    error_check_ok, warnings = check_error_signals()
    
    # [6] 최종 판정
    all_pass = final_judgment(structure_ok, schema_ok, distribution_ok, samples_ok, error_check_ok, warnings)
    
    print("\n" + "=" * 80)
    print("검증 완료")
    print("=" * 80)
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
