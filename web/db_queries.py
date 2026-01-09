"""
Database query helpers for Streamlit dashboard

읽기 전용 (SELECT only)
SQLAlchemy engine을 사용하여 커넥션 풀 재사용
"""
import pandas as pd
from typing import List, Dict, Any, Optional
import streamlit as st
from sqlalchemy import text
import psycopg2

# SQLAlchemy engine 사용 (커넥션 풀 포함)
from common.db import engine
from common.config import DATABASE_URL

def get_db_connection():
    """
    Get database connection from SQLAlchemy engine (커넥션 풀 재사용)
    psycopg2 cursor 호환을 위해 raw connection 반환
    
    Returns:
        psycopg2 connection 또는 None
    """
    if not DATABASE_URL:
        return None
    try:
        # SQLAlchemy engine에서 raw psycopg2 connection 가져오기
        raw_conn = engine.raw_connection()
        return raw_conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def query_to_dataframe(query: str, params: tuple = None) -> pd.DataFrame:
    """
    Execute query and return as DataFrame
    SQLAlchemy engine을 사용하여 커넥션 풀 재사용
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()  # 빈 DataFrame 반환
    try:
        # psycopg2 cursor 사용 (기존 코드 호환)
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        # 예외 발생 시 로깅 (디버깅용)
        print(f"Error executing query: {e}")
        print(f"Query: {query}")
        return pd.DataFrame()  # 빈 DataFrame 반환
    finally:
        if conn:
            conn.close()

def get_executive_overview() -> Dict[str, Any]:
    """Executive Overview 데이터 조회"""
    conn = get_db_connection()
    if conn is None:
        # DB 연결 실패 시 기본값 반환
        return {
            "total_topics": 0,
            "seasonal_count": 0,
            "evergreen_count": 0,
            "aio_available": 0,
            "aio_not_available": 0,
            "aio_error": 0,
            "lg_cited_count": 0,
            "top_topics": []
        }
    try:
        with conn.cursor() as cur:
            # 전체 Master Topic 수 (topic_qa_briefs가 없으면 clusters에서 카운트)
            try:
                cur.execute("""
                    SELECT COUNT(*) as total_topics
                    FROM topic_qa_briefs
                """)
                total_topics = cur.fetchone()[0] or 0
            except Exception as e:
                print(f"Error counting topic_qa_briefs: {e}")
                # topic_qa_briefs가 없으면 clusters에서 카운트
                try:
                    cur.execute("""
                        SELECT COUNT(*) as total_topics
                        FROM clusters
                        WHERE noise_label = FALSE
                    """)
                    total_topics = cur.fetchone()[0] or 0
                except Exception as e2:
                    print(f"Error counting clusters: {e2}")
                    total_topics = 0
            
            # 시즌성 vs 비시즌성 비율
            try:
                cur.execute("""
                    SELECT 
                        category,
                        COUNT(*) as count
                    FROM topic_qa_briefs
                    WHERE category IN ('SPRING_RECIPES', 'SPRING_KITCHEN_STYLING', 
                                        'REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING')
                    GROUP BY category
                """)
                category_counts = {row[0]: row[1] for row in cur.fetchall()}
            except Exception as e:
                print(f"Error counting categories from topic_qa_briefs: {e}")
                # topic_qa_briefs가 없으면 clusters에서 카운트
                try:
                    cur.execute("""
                        SELECT 
                            topic_category,
                            COUNT(*) as count
                        FROM clusters
                        WHERE noise_label = FALSE
                        AND topic_category IN ('SPRING_RECIPES', 'SPRING_KITCHEN_STYLING', 
                                               'REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING')
                        GROUP BY topic_category
                    """)
                    category_counts = {row[0]: row[1] for row in cur.fetchall()}
                except Exception as e2:
                    print(f"Error counting categories from clusters: {e2}")
                    category_counts = {}
            
            seasonal_count = sum(category_counts.get(cat, 0) for cat in ['SPRING_RECIPES', 'SPRING_KITCHEN_STYLING'])
            evergreen_count = sum(category_counts.get(cat, 0) for cat in ['REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING'])
            
            # AIO AVAILABLE vs NOT_AVAILABLE 비율 (aio_status 컬럼이 없을 수 있음)
            aio_counts = {}
            try:
                cur.execute("""
                    SELECT 
                        COALESCE(aio_status, 'UNKNOWN') as aio_status,
                        COUNT(*) as count
                    FROM raw_serp_aio
                    GROUP BY COALESCE(aio_status, 'UNKNOWN')
                """)
                aio_counts = {row[0]: row[1] for row in cur.fetchall()}
            except Exception as e:
                print(f"Error counting aio_status: {e}")
                # aio_status 컬럼이 없으면 전체 카운트만
                try:
                    cur.execute("""
                        SELECT COUNT(*) as total
                        FROM raw_serp_aio
                    """)
                    total_serp = cur.fetchone()[0] or 0
                    if total_serp > 0:
                        aio_counts = {'UNKNOWN': total_serp}
                except Exception as e2:
                    print(f"Error counting raw_serp_aio: {e2}")
                    aio_counts = {}
            
            # LG 도메인 인용된 Topic 수
            lg_cited_count = 0
            try:
                cur.execute("""
                    SELECT COUNT(DISTINCT tqb.cluster_id) as lg_cited_count
                    FROM topic_qa_briefs tqb
                    JOIN raw_serp_aio sa ON sa.query ILIKE '%' || LOWER(tqb.topic_title) || '%'
                    WHERE COALESCE(sa.aio_status, '') = 'AVAILABLE'
                    AND (
                        sa.cited_sources_json::text ILIKE '%lge.com%'
                        OR sa.cited_sources_json::text ILIKE '%lg.com%'
                        OR sa.cited_sources_json::text ILIKE '%lgstory.com%'
                    )
                """)
                lg_cited_count = cur.fetchone()[0] or 0
            except Exception as e:
                print(f"Error counting LG cited topics: {e}")
                lg_cited_count = 0
            
            # 최근 3개월 기준 우선 검토 Master Topic Top 5
            top_topics = []
            try:
                cur.execute("""
                    SELECT 
                        tqb.cluster_id,
                        tqb.topic_title,
                        tqb.category,
                        tqb.score,
                        tqb.insights_json->'evidence_strength'->>'score' as evidence_score
                    FROM topic_qa_briefs tqb
                    JOIN clusters c ON tqb.cluster_id = c.cluster_id
                    WHERE tqb.score IS NOT NULL
                    ORDER BY 
                        COALESCE((tqb.insights_json->'evidence_strength'->>'score')::int, 0) DESC,
                        tqb.score DESC
                    LIMIT 5
                """)
                top_topics = cur.fetchall()
            except Exception as e:
                print(f"Error fetching top topics: {e}")
                top_topics = []
            
            return {
                "total_topics": total_topics,
                "seasonal_count": seasonal_count,
                "evergreen_count": evergreen_count,
                "aio_available": aio_counts.get('AVAILABLE', 0),
                "aio_not_available": aio_counts.get('NOT_AVAILABLE', 0),
                "aio_error": aio_counts.get('ERROR', 0),
                "lg_cited_count": lg_cited_count,
                "top_topics": top_topics
            }
    except Exception as e:
        print(f"Error in get_executive_overview: {e}")
        import traceback
        traceback.print_exc()
        # 예외 발생 시 기본값 반환
        return {
            "total_topics": 0,
            "seasonal_count": 0,
            "evergreen_count": 0,
            "aio_available": 0,
            "aio_not_available": 0,
            "aio_error": 0,
            "lg_cited_count": 0,
            "top_topics": []
        }
    finally:
        if conn:
            conn.close()

def get_reddit_posts(keyword_filter: Optional[str] = None, limit: int = 1000) -> pd.DataFrame:
    """Reddit 포스트 조회"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()  # 빈 DataFrame 반환
    
    try:
        query = """
            SELECT 
                reddit_post_id,
                keyword,
                title,
                upvotes,
                num_comments,
                TO_TIMESTAMP(created_utc) as created_at,
                permalink,
                subreddit
            FROM raw_reddit_posts
        """
        params = None
        if keyword_filter:
            query += " WHERE keyword ILIKE %s"
            params = (f"%{keyword_filter}%",)
        
        query += " ORDER BY upvotes DESC, num_comments DESC LIMIT %s"
        if params:
            params = params + (limit,)
        else:
            params = (limit,)
        
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        # 에러 발생 시 빈 DataFrame 반환 (호출자가 처리)
        print(f"Error in get_reddit_posts: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def get_serp_aio() -> pd.DataFrame:
    """SERP AI Overview 조회 (raw_serp_aio + serp_results 통합)"""
    conn = get_db_connection()
    if conn is None:
        print("Error: Database connection failed in get_serp_aio")
        return pd.DataFrame()
    
    try:
        dfs = []
        
        # 1. raw_serp_aio 테이블 조회
        with conn.cursor() as cur:
            # raw_serp_aio 테이블 존재 여부 확인
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'raw_serp_aio'
                )
            """)
            raw_serp_aio_exists = cur.fetchone()[0]
            
            if raw_serp_aio_exists:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'raw_serp_aio'
                """)
                columns = [row[0] for row in cur.fetchall()]
                has_aio_status = 'aio_status' in columns
                
                if has_aio_status:
                    query_aio = """
                        SELECT 
                            query,
                            COALESCE(aio_status, 'UNKNOWN') as aio_status,
                            aio_text,
                            cited_sources_json,
                            snapshot_at,
                            COALESCE(locale, 'en-US') as locale,
                            'raw_serp_aio' as source_table
                        FROM raw_serp_aio
                        ORDER BY snapshot_at DESC
                    """
                else:
                    query_aio = """
                        SELECT 
                            query,
                            'UNKNOWN' as aio_status,
                            aio_text,
                            cited_sources_json,
                            snapshot_at,
                            COALESCE(locale, 'en-US') as locale,
                            'raw_serp_aio' as source_table
                        FROM raw_serp_aio
                        ORDER BY snapshot_at DESC
                    """
                
                cur.execute("SELECT COUNT(*) FROM raw_serp_aio")
                count_aio = cur.fetchone()[0]
                print(f"raw_serp_aio 테이블 레코드 수: {count_aio}")
                
                if count_aio > 0:
                    df_aio = pd.read_sql_query(query_aio, conn)
                    dfs.append(df_aio)
                    print(f"raw_serp_aio에서 {len(df_aio)}개 레코드 조회")
            
            # 2. serp_results 테이블 조회 (쿼리별로 그룹화)
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'serp_results'
                )
            """)
            serp_results_exists = cur.fetchone()[0]
            
            if serp_results_exists:
                # serp_results에서 쿼리별로 집계하여 raw_serp_aio 형식으로 변환
                # cited_sources_json은 parse_cited_sources 함수가 기대하는 리스트 형식으로 생성
                query_serp = """
                    SELECT 
                        sr.query,
                        'AVAILABLE' as aio_status,
                        NULL as aio_text,
                        jsonb_agg(
                            jsonb_build_object(
                                'url', sr.url,
                                'link', sr.url,
                                'title', sr.title,
                                'snippet', sr.snippet,
                                'position', sr.position,
                                'source', sr.source
                            ) ORDER BY sr.position
                        )::text as cited_sources_json,
                        MAX(sr.fetched_at) as snapshot_at,
                        'en-US' as locale,
                        'serp_results' as source_table
                    FROM serp_results sr
                    WHERE sr.query IS NOT NULL AND sr.query != ''
                    GROUP BY sr.query
                    ORDER BY snapshot_at DESC
                """
                
                # 고유 쿼리 수 확인
                cur.execute("SELECT COUNT(DISTINCT query) FROM serp_results WHERE query IS NOT NULL AND query != ''")
                unique_query_count = cur.fetchone()[0]
                print(f"serp_results 테이블 고유 쿼리 수: {unique_query_count}")
                
                cur.execute("SELECT COUNT(*) FROM serp_results")
                count_serp = cur.fetchone()[0]
                print(f"serp_results 테이블 전체 레코드 수: {count_serp}")
                
                if count_serp > 0:
                    df_serp = pd.read_sql_query(query_serp, conn)
                    dfs.append(df_serp)
                    print(f"serp_results에서 {len(df_serp)}개 쿼리 조회 (예상: {unique_query_count}개)")
        
        # 데이터프레임 통합
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            # 중복 쿼리 제거 (raw_serp_aio 우선)
            # 단, serp_results의 모든 쿼리를 포함하도록 처리
            before_dedup = len(df)
            df = df.drop_duplicates(subset=['query'], keep='first')
            after_dedup = len(df)
            print(f"get_serp_aio() 통합 전: {before_dedup}개, 중복 제거 후: {after_dedup}개")
            return df
        else:
            print("Warning: 두 테이블 모두 데이터가 없습니다.")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error in get_serp_aio: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def get_clustering_results_from_db() -> pd.DataFrame:
    """DB에서 클러스터링 결과 전체 조회 (Clustering Results 탭용)"""
    conn = get_db_connection()
    if conn is None:
        print("⚠️ get_clustering_results_from_db: DB 연결 실패")
        return pd.DataFrame()
    
    try:
        query = """
            SELECT 
                c.cluster_id,
                c.size,
                c.algorithm,
                c.topic_category,
                c.sub_cluster_index,
                c.top_keywords,
                -- 클러스터명 생성: topic_category_sub_cluster_index 형식
                CASE 
                    WHEN c.topic_category IS NOT NULL AND c.sub_cluster_index IS NOT NULL 
                    THEN c.topic_category || '_' || (c.sub_cluster_index + 1)::text
                    ELSE 'Cluster_' || c.cluster_id::text
                END as cluster_name,
                -- 전체 포스트 ID 목록 (JSONB를 텍스트로 변환)
                COALESCE(
                    jsonb_agg(DISTINCT ca.doc_id) FILTER (WHERE ca.doc_id IS NOT NULL)::text,
                    '[]'
                ) as post_ids,
                -- 대표 포스트 ID 목록 (JSONB를 텍스트로 변환)
                COALESCE(
                    jsonb_agg(DISTINCT ca.doc_id) FILTER (WHERE ca.is_representative = TRUE AND ca.doc_id IS NOT NULL)::text,
                    '[]'
                ) as representative_post_ids,
                COUNT(DISTINCT ca.doc_id) FILTER (WHERE ca.is_representative = TRUE) as representative_count
            FROM clusters c
            LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
            WHERE c.noise_label = FALSE
            GROUP BY c.cluster_id, c.size, c.algorithm, c.topic_category, c.sub_cluster_index, c.top_keywords
            ORDER BY c.topic_category, c.sub_cluster_index, c.size DESC
        """
        df = pd.read_sql_query(query, conn)
        
        print(f"✅ get_clustering_results_from_db: {len(df)}개 클러스터 조회됨")
        
        # JSONB 배열을 Python 리스트로 변환
        if len(df) > 0:
            import json
            import numpy as np
            
            def safe_convert_to_list(val):
                """값을 안전하게 리스트로 변환"""
                if val is None:
                    return []
                if isinstance(val, list):
                    return val
                if isinstance(val, np.ndarray):
                    return val.tolist()
                if isinstance(val, str):
                    try:
                        parsed = json.loads(val)
                        return parsed if isinstance(parsed, list) else []
                    except (json.JSONDecodeError, TypeError):
                        return []
                try:
                    # dict나 다른 iterable인 경우
                    if hasattr(val, '__iter__') and not isinstance(val, (str, bytes)):
                        return list(val)
                except:
                    pass
                return []
            
            for idx, row in df.iterrows():
                try:
                    # post_ids 변환
                    post_ids_val = row.get('post_ids')
                    df.at[idx, 'post_ids'] = safe_convert_to_list(post_ids_val)
                    
                    # representative_post_ids 변환
                    rep_post_ids_val = row.get('representative_post_ids')
                    df.at[idx, 'representative_post_ids'] = safe_convert_to_list(rep_post_ids_val)
                    
                    # top_keywords 변환
                    top_keywords_val = row.get('top_keywords')
                    df.at[idx, 'top_keywords'] = safe_convert_to_list(top_keywords_val)
                    
                except Exception as row_error:
                    print(f"⚠️ 행 {idx} 처리 중 오류: {row_error}")
                    import traceback
                    traceback.print_exc()
                    # 기본값 설정
                    df.at[idx, 'post_ids'] = []
                    df.at[idx, 'representative_post_ids'] = []
                    df.at[idx, 'top_keywords'] = []
        
        return df
    except Exception as e:
        print(f"❌ Error in get_clustering_results_from_db: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def get_clusters_with_trends() -> pd.DataFrame:
    """클러스터 및 트렌드 정보 조회"""
    query = """
        SELECT 
            c.cluster_id,
            c.size,
            c.algorithm,
            c.topic_category,
            c.sub_cluster_index,
            c.top_keywords,
            c.monthly_trend_summary,
            c.representative_posts_summary,
            COUNT(DISTINCT ca.doc_id) FILTER (WHERE ca.is_representative = TRUE) as representative_count,
            (SELECT category FROM topic_qa_briefs WHERE cluster_id = c.cluster_id LIMIT 1) as category,
            -- 클러스터명 생성: topic_category_sub_cluster_index 형식 (예: SPRING_RECIPES_1)
            CASE 
                WHEN c.topic_category IS NOT NULL AND c.sub_cluster_index IS NOT NULL 
                THEN c.topic_category || '_' || (c.sub_cluster_index + 1)::text
                ELSE 'Cluster_' || c.cluster_id::text
            END as cluster_name
        FROM clusters c
        LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
        WHERE c.noise_label = FALSE
        GROUP BY c.cluster_id, c.size, c.algorithm, c.topic_category, c.sub_cluster_index, c.top_keywords, c.monthly_trend_summary, c.representative_posts_summary
        ORDER BY c.size DESC
    """
    return query_to_dataframe(query)

def get_cluster_summary_from_db(cluster_id: str) -> Optional[str]:
    """DB에서 클러스터 요약 조회 (cluster_id 문자열로 매칭)"""
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            # cluster_id가 문자열인 경우 topic_category와 sub_cluster_index로 매칭 시도
            # 예: "SPRING_RECIPES_1" -> topic_category="SPRING_RECIPES", sub_cluster_index=1
            if isinstance(cluster_id, str) and '_' in cluster_id:
                parts = cluster_id.rsplit('_', 1)
                if len(parts) == 2:
                    topic_category = parts[0]
                    try:
                        sub_cluster_index = int(parts[1]) - 1  # JSON은 1부터 시작, DB는 0부터 시작할 수 있음
                        cur.execute("""
                            SELECT summary
                            FROM clusters
                            WHERE topic_category = %s 
                            AND sub_cluster_index = %s
                            LIMIT 1
                        """, (topic_category, sub_cluster_index))
                        result = cur.fetchone()
                        if result and result[0]:
                            return result[0]
                    except ValueError:
                        pass
            
            # 정수형 cluster_id로 직접 조회 시도
            try:
                cluster_id_int = int(cluster_id) if isinstance(cluster_id, str) else cluster_id
                cur.execute("""
                    SELECT summary
                    FROM clusters
                    WHERE cluster_id = %s
                    LIMIT 1
                """, (cluster_id_int,))
                result = cur.fetchone()
                if result and result[0]:
                    return result[0]
            except (ValueError, TypeError):
                pass
            
            return None
    finally:
        conn.close()

def get_cluster_timeseries(cluster_id: int) -> pd.DataFrame:
    """클러스터 시계열 데이터 조회"""
    # numpy.int64 타입 오류 수정: cluster_id를 Python int로 변환
    import numpy as np
    if isinstance(cluster_id, (np.integer, np.int64)):
        cluster_id = int(cluster_id)
    elif pd.api.types.is_integer(cluster_id):
        cluster_id = int(cluster_id)
    
    query = """
        SELECT 
            month,
            reddit_post_count,
            reddit_weighted_score
        FROM cluster_timeseries
        WHERE cluster_id = %s
        ORDER BY month DESC
    """
    return query_to_dataframe(query, (cluster_id,))

def get_cluster_representative_posts(cluster_id: int, limit: int = 5) -> pd.DataFrame:
    """클러스터 대표 포스트 조회"""
    # numpy.int64 타입 오류 수정: cluster_id를 Python int로 변환
    import numpy as np
    if isinstance(cluster_id, (np.integer, np.int64)):
        cluster_id = int(cluster_id)
    elif pd.api.types.is_integer(cluster_id):
        cluster_id = int(cluster_id)
    
    query = """
        SELECT 
            rp.reddit_post_id,
            rp.title,
            rp.body,
            rp.upvotes,
            rp.num_comments,
            rp.permalink,
            rp.keyword,
            TO_TIMESTAMP(rp.created_utc) as created_at
        FROM raw_reddit_posts rp
        JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
        WHERE ca.cluster_id = %s
        AND ca.is_representative = TRUE
        ORDER BY rp.upvotes DESC
        LIMIT %s
    """
    return query_to_dataframe(query, (cluster_id, limit))

def get_cluster_gpt_summaries(cluster_id: int) -> Dict[str, Optional[str]]:
    """클러스터의 GPT 요약 조회 (월간 트렌드 및 대표 포스트)"""
    conn = get_db_connection()
    if conn is None:
        return {"monthly_trend_summary": None, "representative_posts_summary": None}
    
    try:
        with conn.cursor() as cur:
            # numpy.int64 타입 오류 수정: cluster_id를 Python int로 변환
            import numpy as np
            if isinstance(cluster_id, (np.integer, np.int64)):
                cluster_id = int(cluster_id)
            elif pd.api.types.is_integer(cluster_id):
                cluster_id = int(cluster_id)
            
            cur.execute("""
                SELECT 
                    monthly_trend_summary,
                    representative_posts_summary
                FROM clusters
                WHERE cluster_id = %s
                LIMIT 1
            """, (cluster_id,))
            result = cur.fetchone()
            
            if result:
                return {
                    "monthly_trend_summary": result[0],
                    "representative_posts_summary": result[1]
                }
            else:
                return {"monthly_trend_summary": None, "representative_posts_summary": None}
    finally:
        conn.close()

def get_master_topics(category_filter: Optional[str] = None, 
                     trend_filter: Optional[str] = None,
                     aio_filter: Optional[str] = None,
                     lg_cited_filter: Optional[bool] = None) -> pd.DataFrame:
    """Master Topic 조회 (필터 지원)"""
    query = """
        SELECT 
            tqb.id,
            tqb.cluster_id,
            tqb.category,
            tqb.topic_title,
            tqb.primary_question,
            tqb.related_questions_json,
            tqb.score,
            tqb.insights_json->'evidence_strength'->>'score' as evidence_score,
            tqb.why_now_json,
            tqb.blog_angle,
            tqb.social_angle,
            tqb.evidence_pack_json,
            tqb.insights_json,
            c.size as cluster_size
        FROM topic_qa_briefs tqb
        JOIN clusters c ON tqb.cluster_id = c.cluster_id
        WHERE 1=1
    """
    params = []
    
    if category_filter:
        query += " AND tqb.category = %s"
        params.append(category_filter)
    
    query += " ORDER BY tqb.score DESC NULLS LAST"
    
    return query_to_dataframe(query, tuple(params) if params else None)

def get_serp_aio_audit() -> pd.DataFrame:
    """SERP AI Overview Audit 데이터 조회"""
    query = """
        SELECT 
            sa.query,
            sa.aio_status,
            sa.aio_text,
            sa.cited_sources_json,
            sa.snapshot_at,
            (SELECT topic_title FROM topic_qa_briefs 
             WHERE cluster_id IN (
                 SELECT DISTINCT ca.cluster_id 
                 FROM cluster_assignments ca
                 JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
                 WHERE rp.keyword ILIKE '%' || sa.query || '%'
                 LIMIT 1
             ) LIMIT 1) as master_topic
        FROM raw_serp_aio sa
        ORDER BY sa.snapshot_at DESC
    """
    return query_to_dataframe(query)

def check_lg_domain(url: str) -> bool:
    """URL이 LG 도메인인지 확인"""
    if not url:
        return False
    lg_domains = ['lge.com', 'lg.com', 'lgstory.com', 'lg.co.kr']
    url_lower = url.lower()
    return any(domain in url_lower for domain in lg_domains)

def parse_cited_sources(cited_sources_json: Any) -> List[Dict[str, Any]]:
    """Cited sources JSON 파싱 (리스트 또는 {'sources': [...]} 형식 지원)"""
    if not cited_sources_json:
        return []
    
    if isinstance(cited_sources_json, str):
        import json
        try:
            cited_sources_json = json.loads(cited_sources_json)
        except:
            return []
    
    # {'sources': [...]} 형식 처리
    if isinstance(cited_sources_json, dict):
        if 'sources' in cited_sources_json:
            cited_sources_json = cited_sources_json['sources']
        else:
            # 딕셔너리 자체가 하나의 소스인 경우
            cited_sources_json = [cited_sources_json]
    
    if not isinstance(cited_sources_json, list):
        return []
    
    sources = []
    for source in cited_sources_json:
        if isinstance(source, dict):
            url = source.get('link') or source.get('url') or ''
            domain = ''
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace('www.', '')
                except:
                    domain = url.split('/')[2] if len(url.split('/')) > 2 else url
            
            sources.append({
                'url': url,
                'domain': domain,
                'title': source.get('title', ''),
                'is_lg': check_lg_domain(url),
                'type': 'brand' if check_lg_domain(url) else ('media' if any(d in domain for d in ['cnn', 'bbc', 'nytimes']) else 'community')
            })
    
    return sources

def get_reddit_clustering_for_master_topic(topic_category: str) -> List[Dict[str, Any]]:
    """마스터 토픽 생성을 위한 Reddit 클러스터링 결과 조회"""
    conn = get_db_connection()
    if conn is None:
        print("⚠️ get_reddit_clustering_for_master_topic: DB 연결 실패")
        return []
    
    try:
        with conn.cursor() as cur:
            # 먼저 해당 topic_category의 클러스터가 있는지 확인
            cur.execute("""
                SELECT COUNT(*) 
                FROM clusters 
                WHERE noise_label = FALSE 
                AND topic_category = %s
            """, (topic_category,))
            cluster_count = cur.fetchone()[0]
            print(f"📊 {topic_category} 카테고리의 클러스터 수: {cluster_count}개")
            
            if cluster_count == 0:
                # topic_category가 NULL인 경우도 확인
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM clusters 
                    WHERE noise_label = FALSE 
                    AND topic_category IS NULL
                """)
                null_count = cur.fetchone()[0]
                print(f"ℹ️ topic_category가 NULL인 클러스터 수: {null_count}개")
                
                # 전체 클러스터 수 확인
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM clusters 
                    WHERE noise_label = FALSE
                """)
                total_count = cur.fetchone()[0]
                print(f"ℹ️ 전체 클러스터 수 (noise 제외): {total_count}개")
            
            query = """
                SELECT 
                    c.cluster_id,
                    c.topic_category,
                    c.sub_cluster_index,
                    c.size as cluster_size,
                    c.top_keywords,
                    -- 대표 포스트 요약 (상위 3개 포스트의 제목과 본문 일부)
                    COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'title', rp.title,
                                'body', LEFT(rp.body, 500),
                                'upvotes', rp.upvotes
                            ) ORDER BY rp.upvotes DESC
                        ) FILTER (WHERE ca.is_representative = TRUE AND ca.doc_type = 'reddit_post' AND rp.title IS NOT NULL),
                        '[]'::jsonb
                    ) as representative_posts
                FROM clusters c
                LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id AND ca.doc_type = 'reddit_post'
                LEFT JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
                WHERE c.noise_label = FALSE
                AND c.topic_category = %s
                GROUP BY c.cluster_id, c.topic_category, c.sub_cluster_index, c.size, c.top_keywords
                ORDER BY c.sub_cluster_index, c.size DESC
            """
            cur.execute(query, (topic_category,))
            results = cur.fetchall()
            
            print(f"✅ {topic_category} 카테고리 클러스터 {len(results)}개 조회됨")
            
            clusters = []
            for row in results:
                cluster_id, topic_cat, sub_idx, size, top_keywords, rep_posts = row
                
                # top_keywords를 리스트로 변환
                keywords_list = []
                if top_keywords:
                    import json
                    if isinstance(top_keywords, str):
                        try:
                            keywords_list = json.loads(top_keywords)
                        except:
                            keywords_list = []
                    elif isinstance(top_keywords, list):
                        keywords_list = top_keywords
                
                # representative_posts를 리스트로 변환
                posts_list = []
                if rep_posts:
                    import json
                    if isinstance(rep_posts, str):
                        try:
                            posts_list = json.loads(rep_posts)
                        except:
                            posts_list = []
                    elif isinstance(rep_posts, list):
                        posts_list = rep_posts
                
                clusters.append({
                    'cluster_id': cluster_id,
                    'topic_category': topic_cat,
                    'sub_cluster_id': sub_idx,
                    'cluster_size': size,
                    'top_keywords': keywords_list[:20] if keywords_list else [],  # 상위 20개만
                    'summary': None,  # DB summary 제거, GPT 요약만 사용
                    'representative_posts': posts_list[:3] if posts_list else []  # 상위 3개만
                })
            
            return clusters
    except Exception as e:
        print(f"❌ Error in get_reddit_clustering_for_master_topic: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            conn.close()

def get_serp_questions_for_master_topic(topic_category: str) -> List[str]:
    """마스터 토픽 생성을 위한 SERP 질문형 키워드 조회"""
    conn = get_db_connection()
    if conn is None:
        print("⚠️ get_serp_questions_for_master_topic: DB 연결 실패")
        return []
    
    try:
        with conn.cursor() as cur:
            queries = []
            
            # 1. serp_results 테이블 확인 (topic_category가 있는 테이블)
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'serp_results'
                )
            """)
            serp_results_exists = cur.fetchone()[0]
            
            if serp_results_exists:
                # serp_results에 topic_category 컬럼이 있는지 확인
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'serp_results' AND column_name = 'topic_category'
                """)
                has_topic_category_sr = cur.fetchone() is not None
                
                if has_topic_category_sr:
                    # topic_category로 필터링
                    query = """
                        SELECT DISTINCT query
                        FROM serp_results
                        WHERE topic_category = %s
                        AND query IS NOT NULL
                        AND query != ''
                        ORDER BY query
                        LIMIT 100
                    """
                    cur.execute(query, (topic_category,))
                    serp_queries = [row[0] for row in cur.fetchall()]
                    print(f"✅ serp_results에서 {len(serp_queries)}개 쿼리 조회 (topic_category={topic_category})")
                    queries.extend(serp_queries)
                else:
                    print("⚠️ serp_results 테이블에 topic_category 컬럼이 없습니다.")
            
            # 2. raw_serp_aio 테이블 확인 (topic_category가 없을 수 있음)
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'raw_serp_aio'
                )
            """)
            raw_serp_aio_exists = cur.fetchone()[0]
            
            if raw_serp_aio_exists:
                # raw_serp_aio에 topic_category 컬럼이 있는지 확인
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'raw_serp_aio' AND column_name = 'topic_category'
                """)
                has_topic_category_aio = cur.fetchone() is not None
                
                if has_topic_category_aio:
                    # topic_category로 필터링
                    query = """
                        SELECT DISTINCT query
                        FROM raw_serp_aio
                        WHERE topic_category = %s
                        AND query IS NOT NULL
                        AND query != ''
                        ORDER BY query
                        LIMIT 100
                    """
                    cur.execute(query, (topic_category,))
                    aio_queries = [row[0] for row in cur.fetchall()]
                    print(f"✅ raw_serp_aio에서 {len(aio_queries)}개 쿼리 조회 (topic_category={topic_category})")
                    queries.extend(aio_queries)
                else:
                    # topic_category가 없으면 전체 조회 (디버깅용)
                    query = """
                        SELECT DISTINCT query
                        FROM raw_serp_aio
                        WHERE query IS NOT NULL
                        AND query != ''
                        ORDER BY query
                        LIMIT 200
                    """
                    cur.execute(query)
                    all_aio_queries = [row[0] for row in cur.fetchall()]
                    print(f"ℹ️ raw_serp_aio에서 전체 {len(all_aio_queries)}개 쿼리 조회 (topic_category 컬럼 없음)")
                    # 일단 전체를 포함 (나중에 필터링 가능)
                    queries.extend(all_aio_queries)
            
            # 중복 제거
            unique_queries = list(set(queries))
            print(f"📊 중복 제거 전: {len(queries)}개, 중복 제거 후: {len(unique_queries)}개")
            
            # 질문형 키워드만 필터링 (?, how, what, why, when, where로 시작하거나 포함)
            question_queries = [
                q for q in unique_queries 
                if any(q.lower().startswith(prefix) or '?' in q.lower() 
                       for prefix in ['how', 'what', 'why', 'when', 'where', 'which', 'who', 'can', 'should', 'is', 'are', 'do', 'does'])
            ]
            
            print(f"✅ 질문형 키워드 필터링 후: {len(question_queries)}개")
            
            return question_queries[:100]  # 최대 100개
    except Exception as e:
        print(f"❌ Error in get_serp_questions_for_master_topic: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            conn.close()
