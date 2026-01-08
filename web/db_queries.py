"""
Database query helpers for Streamlit dashboard

읽기 전용 (SELECT only)
"""
import psycopg2
import pandas as pd
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

def get_db_connection():
    """Get database connection from DATABASE_URL"""
    # Railway PostgreSQL 플러그인은 DATABASE_URL을 자동으로 설정
    # 또는 RAILWAY_DATABASE_URL, POSTGRES_URL 등도 확인
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or 
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    if not database_url:
        # 에러를 발생시키지 않고 None 반환 (호출자가 처리)
        return None
    try:
        return psycopg2.connect(database_url)
    except Exception as e:
        # 연결 실패 시 None 반환
        return None

def query_to_dataframe(query: str, params: tuple = None) -> pd.DataFrame:
    """Execute query and return as DataFrame"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()  # 빈 DataFrame 반환
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
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
            # 전체 Master Topic 수
            cur.execute("""
                SELECT COUNT(*) as total_topics
                FROM topic_qa_briefs
            """)
            total_topics = cur.fetchone()[0] or 0
            
            # 시즌성 vs 비시즌성 비율
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
            
            seasonal_count = sum(category_counts.get(cat, 0) for cat in ['SPRING_RECIPES', 'SPRING_KITCHEN_STYLING'])
            evergreen_count = sum(category_counts.get(cat, 0) for cat in ['REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING'])
            
            # AIO AVAILABLE vs NOT_AVAILABLE 비율
            cur.execute("""
                SELECT 
                    aio_status,
                    COUNT(*) as count
                FROM raw_serp_aio
                GROUP BY aio_status
            """)
            aio_counts = {row[0]: row[1] for row in cur.fetchall()}
            
            # LG 도메인 인용된 Topic 수
            # (cited_sources_json에서 LG 도메인 체크)
            cur.execute("""
                SELECT COUNT(DISTINCT tqb.cluster_id) as lg_cited_count
                FROM topic_qa_briefs tqb
                JOIN raw_serp_aio sa ON sa.query ILIKE '%' || LOWER(tqb.topic_title) || '%'
                WHERE sa.aio_status = 'AVAILABLE'
                AND (
                    sa.cited_sources_json::text ILIKE '%lge.com%'
                    OR sa.cited_sources_json::text ILIKE '%lg.com%'
                    OR sa.cited_sources_json::text ILIKE '%lgstory.com%'
                )
            """)
            lg_cited_count = cur.fetchone()[0] or 0
            
            # 최근 3개월 기준 우선 검토 Master Topic Top 5
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
    finally:
        conn.close()

def get_reddit_posts(keyword_filter: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
    """Reddit 포스트 조회"""
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
    
    return query_to_dataframe(query, params)

def get_serp_aio() -> pd.DataFrame:
    """SERP AI Overview 조회"""
    query = """
        SELECT 
            query,
            aio_status,
            aio_text,
            cited_sources_json,
            snapshot_at,
            locale
        FROM raw_serp_aio
        ORDER BY snapshot_at DESC
    """
    return query_to_dataframe(query)

def get_clusters_with_trends() -> pd.DataFrame:
    """클러스터 및 트렌드 정보 조회"""
    query = """
        SELECT 
            c.cluster_id,
            c.size,
            c.algorithm,
            COUNT(DISTINCT ca.doc_id) FILTER (WHERE ca.is_representative = TRUE) as representative_count,
            (SELECT category FROM topic_qa_briefs WHERE cluster_id = c.cluster_id LIMIT 1) as category
        FROM clusters c
        LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
        WHERE c.noise_label = FALSE
        GROUP BY c.cluster_id, c.size, c.algorithm
        ORDER BY c.size DESC
    """
    return query_to_dataframe(query)

def get_cluster_timeseries(cluster_id: int) -> pd.DataFrame:
    """클러스터 시계열 데이터 조회"""
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
    """Cited sources JSON 파싱"""
    if not cited_sources_json:
        return []
    
    if isinstance(cited_sources_json, str):
        import json
        try:
            cited_sources_json = json.loads(cited_sources_json)
        except:
            return []
    
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
