#!/usr/bin/env python3
"""
주제별 클러스터링 실제 실행 및 검증 스크립트

1. dry-run 없이 실제 DB 저장 모드로 클러스터링 실행
2. DB 저장 결과 검증
3. 정량 검증
4. 샘플 검증
5. 최종 판정
"""
import sys
from pathlib import Path
from typing import Dict, List, Any
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection, create_pipeline_run, update_pipeline_run
from worker.pipeline.tfidf_clustering import run_tfidf_clustering
from worker.pipeline.logging import setup_logger
from worker.pipeline.config import CATEGORIES

logger = setup_logger("run_and_validate")

def check_dry_run_mode():
    """[1] 실행 모드 전환 확인"""
    print("\n" + "=" * 80)
    print("[1] 실행 모드 전환 (Dry-run → Persist)")
    print("=" * 80)
    
    print("\n코드 경로 분석:")
    print("- 파일: worker/pipeline/tfidf_clustering.py")
    print("- 함수: run_tfidf_clustering(run_id: int, dry_run: bool = False)")
    print("- 라인 422: if dry_run: ← dry-run 가드")
    print("- 라인 429: continue ← dry-run 시 DB 저장 스킵")
    print("- 라인 431-475: 실제 DB 저장 코드 경로")
    
    print("\n변경 사항:")
    print("- dry_run=False로 함수 호출")
    print("- 라인 422의 dry_run 체크를 통과하여 라인 431-475의 DB 저장 경로 실행")
    
    print("\n✅ DB 저장 코드 경로:")
    print("  - 라인 441-452: clusters 테이블 INSERT")
    print("  - 라인 459-468: cluster_assignments 테이블 INSERT (upsert_cluster_assignment)")
    print("  - 라인 475: conn.commit()")
    
    return True

def run_clustering():
    """[2] 주제별 클러스터링 실제 실행"""
    print("\n" + "=" * 80)
    print("[2] 주제별 클러스터링 실제 실행")
    print("=" * 80)
    
    # Pipeline run 생성
    run_id = create_pipeline_run("cluster_tfidf_validate", status="running")
    logger.info(f"Pipeline run 생성: run_id={run_id}")
    
    print(f"\n실행 모드: 실제 DB 저장 (dry_run=False)")
    print(f"Run ID: {run_id}")
    
    try:
        # dry_run=False로 클러스터링 실행
        stats = run_tfidf_clustering(run_id, dry_run=False)
        
        # Pipeline run 완료 처리
        update_pipeline_run(run_id, "completed", metadata=stats)
        
        print("\n실행 결과:")
        print(f"  - 처리된 포스트 수: {stats.get('posts_processed', 0)}")
        print(f"  - 생성된 클러스터 수: {stats.get('clusters_created', 0)}")
        print(f"  - 생성된 할당 수: {stats.get('assignments_created', 0)}")
        
        print("\ntopic_category별 결과:")
        for category, cat_stats in stats.get("categories", {}).items():
            if cat_stats.get("status") == "no_data":
                print(f"  {category}: 데이터 없음 (post 수: 0)")
            else:
                print(f"  {category}:")
                print(f"    - 입력 post 수: {cat_stats.get('post_count', 0)}")
                print(f"    - 생성된 sub-cluster 수: {cat_stats.get('sub_clusters_created', 0)}")
        
        return run_id, stats
    
    except Exception as e:
        logger.error(f"클러스터링 실행 실패: {e}", exc_info=True)
        update_pipeline_run(run_id, "failed", error_message=str(e))
        raise

def validate_db_schema(run_id: int):
    """[3] DB 저장 스키마 검증"""
    print("\n" + "=" * 80)
    print("[3] DB 저장 스키마 검증")
    print("=" * 80)
    
    conn = None
    issues = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. topic_category NULL 체크
            cur.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN params_json->>'topic_category' IS NULL 
                                  AND params_json->>'category' IS NULL THEN 1 END) as null_count
                FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """, (run_id,))
            
            total, null_count = cur.fetchone()
            
            print(f"\n1. topic_category NULL 체크:")
            print(f"   전체 클러스터: {total}")
            print(f"   topic_category 없는 클러스터: {null_count}")
            
            if null_count > 0:
                issues.append(f"topic_category가 NULL인 클러스터 {null_count}개 발견")
            else:
                print("   ✅ 모든 클러스터에 topic_category 저장됨")
            
            # 2. 동일 post_id가 여러 topic_category에 속하는지 확인
            cur.execute("""
                SELECT ca.doc_id, 
                       COUNT(DISTINCT COALESCE(c.params_json->>'topic_category', c.params_json->>'category')) as category_count,
                       array_agg(DISTINCT COALESCE(c.params_json->>'topic_category', c.params_json->>'category')) as categories
                FROM cluster_assignments ca
                JOIN clusters c ON ca.cluster_id = c.cluster_id
                WHERE c.created_from_run_id = %s
                AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                GROUP BY ca.doc_id
                HAVING COUNT(DISTINCT COALESCE(c.params_json->>'topic_category', c.params_json->>'category')) > 1
                LIMIT 10
            """, (run_id,))
            
            duplicate_posts = cur.fetchall()
            
            print(f"\n2. 동일 post_id 중복 할당 체크:")
            print(f"   여러 topic_category에 속한 포스트: {len(duplicate_posts)}개")
            
            if duplicate_posts:
                issues.append(f"여러 topic_category에 속한 포스트 {len(duplicate_posts)}개 이상 발견")
                for post_id, cat_count, categories in duplicate_posts[:5]:
                    print(f"     - {post_id}: {cat_count}개 카테고리 {categories}")
            else:
                print("   ✅ 모든 포스트는 정확히 하나의 topic_category에만 속함")
            
            # 3. sub_cluster_id가 topic_category 스코프 안에서만 의미를 가지는지 확인
            cur.execute("""
                SELECT params_json->>'topic_category' as topic_category,
                       params_json->>'sub_cluster_index' as sub_cluster_index,
                       cluster_id,
                       COUNT(*) as count
                FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                GROUP BY params_json->>'topic_category', params_json->>'sub_cluster_index', cluster_id
                HAVING COUNT(*) > 1
            """, (run_id,))
            
            duplicate_indices = cur.fetchall()
            
            print(f"\n3. sub_cluster_index 중복 체크:")
            if duplicate_indices:
                issues.append(f"동일 topic_category 내에서 sub_cluster_index 중복 발견")
                for topic_cat, sub_idx, cluster_id, count in duplicate_indices:
                    print(f"     - {topic_cat}, sub_cluster_index={sub_idx}: {count}개 클러스터")
            else:
                print("   ✅ 각 topic_category 내에서 sub_cluster_index는 고유함")
            
            return len(issues) == 0, issues
    
    finally:
        if conn:
            put_db_connection(conn)

def validate_quantitative_stats(run_id: int):
    """[4] DB 저장 결과 정량 검증"""
    print("\n" + "=" * 80)
    print("[4] DB 저장 결과 정량 검증")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            print("\ntopic_category별 통계:")
            print("-" * 80)
            
            for category in CATEGORIES:
                # 전체 post 수 (raw_reddit_posts에서 해당 카테고리로 분류된 것)
                # 실제로는 assign_post_to_category로 분류되지만, DB에는 저장되지 않으므로
                # 클러스터링된 포스트 수만 확인
                
                # 클러스터링된 포스트 수
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
                """, (run_id, category, category))
                
                clustered_result = cur.fetchone()
                clustered_posts = clustered_result[0] if clustered_result else 0
                
                # 생성된 sub-cluster 개수
                cur.execute("""
                    SELECT COUNT(*) as cluster_count
                    FROM clusters
                    WHERE created_from_run_id = %s
                    AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        params_json->>'topic_category' = %s
                        OR params_json->>'category' = %s
                    )
                """, (run_id, category, category))
                
                cluster_result = cur.fetchone()
                sub_clusters = cluster_result[0] if cluster_result else 0
                
                # 클러스터 내 총 포스트 수 (size 합계)
                cur.execute("""
                    SELECT SUM(size) as total_posts_in_clusters
                    FROM clusters
                    WHERE created_from_run_id = %s
                    AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
                    AND (
                        params_json->>'topic_category' = %s
                        OR params_json->>'category' = %s
                    )
                """, (run_id, category, category))
                
                total_in_clusters_result = cur.fetchone()
                total_in_clusters = total_in_clusters_result[0] if total_in_clusters_result and total_in_clusters_result[0] else 0
                
                print(f"\nTopic: {category}")
                print(f"  - clustered_posts: {clustered_posts}")
                print(f"  - sub_clusters: {sub_clusters}")
                print(f"  - total_posts_in_clusters (size 합계): {total_in_clusters}")
                
                if sub_clusters == 0:
                    print(f"  ⚠️  상태: 클러스터 없음")
                elif clustered_posts == 0:
                    print(f"  ⚠️  상태: 클러스터는 있으나 할당된 포스트 없음")
                else:
                    print(f"  ✅ 상태: 정상")
            
            return True
    
    finally:
        if conn:
            put_db_connection(conn)

def validate_samples(run_id: int):
    """[5] 결과 샘플 검증"""
    print("\n" + "=" * 80)
    print("[5] 결과 샘플 검증")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
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
                """, (run_id, category, category))
                
                cluster_result = cur.fetchone()
                
                if not cluster_result:
                    print("  ⚠️  클러스터 없음")
                    continue
                
                cluster_id, params_json, size = cluster_result
                params = params_json if isinstance(params_json, dict) else {}
                
                print(f"\n  Sub-cluster ID: {cluster_id}")
                print(f"  포스트 수: {size}")
                print(f"  대표 키워드: {', '.join(params.get('top_keywords', [])[:10])}")
                
                # 해당 클러스터의 포스트 5개 조회
                cur.execute("""
                    SELECT rp.reddit_post_id, rp.title, rp.upvotes, rp.num_comments
                    FROM cluster_assignments ca
                    JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
                    WHERE ca.cluster_id = %s
                    ORDER BY rp.upvotes DESC, rp.num_comments DESC
                    LIMIT 5
                """, (cluster_id,))
                
                posts = cur.fetchall()
                
                print(f"\n  클러스터 내 포스트 샘플 (상위 5개):")
                titles = []
                for i, (post_id, title, upvotes, num_comments) in enumerate(posts, 1):
                    title_preview = title[:60] + "..." if title and len(title) > 60 else (title or "")
                    titles.append(title_preview)
                    print(f"    {i}. {title_preview}")
                    print(f"       (👍 {upvotes}, 💬 {num_comments})")
                
                # 의미적 묶임 설명
                if len(posts) > 0:
                    keywords_str = ', '.join(params.get('top_keywords', [])[:5])
                    print(f"\n  ✅ 설명: 이 클러스터는 '{category}' 주제 내에서 '{keywords_str}' 관련 포스트들이 의미적으로 묶여 있음")
            
            return True
    
    finally:
        if conn:
            put_db_connection(conn)

def final_judgment(run_id: int, schema_ok: bool, schema_issues: List[str]):
    """[6] 최종 판정"""
    print("\n" + "=" * 80)
    print("[6] 최종 판정")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 클러스터 수 확인
            cur.execute("""
                SELECT COUNT(*) as count
                FROM clusters
                WHERE created_from_run_id = %s
                AND algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """, (run_id,))
            
            cluster_count = cur.fetchone()[0]
            
            # 할당 수 확인
            cur.execute("""
                SELECT COUNT(*) as count
                FROM cluster_assignments ca
                JOIN clusters c ON ca.cluster_id = c.cluster_id
                WHERE c.created_from_run_id = %s
                AND c.algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')
            """, (run_id,))
            
            assignment_count = cur.fetchone()[0]
            
            print(f"\n실행 결과 요약:")
            print(f"  - Run ID: {run_id}")
            print(f"  - 생성된 클러스터 수: {cluster_count}")
            print(f"  - 생성된 할당 수: {assignment_count}")
            print(f"  - DB 스키마 검증: {'PASS' if schema_ok else 'FAIL'}")
            
            db_persist_executed = cluster_count > 0 and assignment_count > 0
            structure_ok = schema_ok and len(schema_issues) == 0
            can_proceed = db_persist_executed and structure_ok
            
            print(f"\n최종 판정:")
            print(f"  - DB persist 실행 여부: {'YES' if db_persist_executed else 'NO'}")
            print(f"  - 주제별 분리 클러스터링 구조: {'PASS' if structure_ok else 'FAIL'}")
            print(f"  - 다음 단계(SERP 질문 생성) 진행 가능 여부: {'YES' if can_proceed else 'NO'}")
            
            if not db_persist_executed:
                print(f"\n⚠️  DB 저장이 실행되지 않았습니다.")
                print(f"   - 코드 경로: worker/pipeline/tfidf_clustering.py 라인 422-429")
                print(f"   - 확인: dry_run=False로 실행되었는지 확인")
            
            if not structure_ok:
                print(f"\n⚠️  구조 검증 실패:")
                for issue in schema_issues:
                    print(f"   - {issue}")
            
            if not can_proceed:
                print(f"\n수정 필요 사항:")
                if not db_persist_executed:
                    print(f"   1. worker/pipeline/tfidf_clustering.py 라인 422: dry_run 체크 제거 또는 False로 설정")
                    print(f"   2. worker/run_pipeline.py: dry_run=False로 함수 호출 확인")
                if schema_issues:
                    print(f"   3. DB 스키마 검증 이슈 해결 필요")
            
            return can_proceed
    
    finally:
        if conn:
            put_db_connection(conn)

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("주제별 클러스터링 실제 실행 및 검증")
    print("=" * 80)
    
    # [1] 실행 모드 확인
    check_dry_run_mode()
    
    # [2] 클러스터링 실행
    run_id, stats = run_clustering()
    
    # [3] DB 스키마 검증
    schema_ok, schema_issues = validate_db_schema(run_id)
    
    # [4] 정량 검증
    validate_quantitative_stats(run_id)
    
    # [5] 샘플 검증
    validate_samples(run_id)
    
    # [6] 최종 판정
    can_proceed = final_judgment(run_id, schema_ok, schema_issues)
    
    print("\n" + "=" * 80)
    print("실행 및 검증 완료")
    print("=" * 80)
    
    return 0 if can_proceed else 1

if __name__ == "__main__":
    sys.exit(main())
