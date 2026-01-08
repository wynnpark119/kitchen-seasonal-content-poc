"""
Database connection and helper functions
"""
import psycopg2
from psycopg2.extras import execute_values, Json
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Optional, Dict, Any, List
import os
from datetime import datetime

def get_db_connection():
    """Get database connection from DATABASE_URL"""
    database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    return psycopg2.connect(database_url)

def create_pipeline_run(run_type: str, status: str = "running") -> int:
    """Create a new pipeline run and return run_id"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pipeline_runs (run_type, status, started_at)
                VALUES (%s, %s, %s)
                RETURNING run_id
            """, (run_type, status, datetime.utcnow()))
            run_id = cur.fetchone()[0]
            conn.commit()
            return run_id
    finally:
        conn.close()

def update_pipeline_run(run_id: int, status: str, error_message: Optional[str] = None, metadata: Optional[Dict] = None):
    """Update pipeline run status"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if status == "completed":
                cur.execute("""
                    UPDATE pipeline_runs
                    SET status = %s, completed_at = %s, metadata = %s
                    WHERE run_id = %s
                """, (status, datetime.utcnow(), Json(metadata) if metadata else None, run_id))
            else:
                cur.execute("""
                    UPDATE pipeline_runs
                    SET status = %s, error_message = %s, metadata = %s
                    WHERE run_id = %s
                """, (status, error_message, Json(metadata) if metadata else None, run_id))
            conn.commit()
    finally:
        conn.close()

def upsert_reddit_post(post_data: Dict[str, Any], run_id: int) -> bool:
    """Upsert Reddit post (insert or update if exists)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO raw_reddit_posts (
                    reddit_post_id, subreddit, title, body, author,
                    created_utc, upvotes, num_comments, permalink, url,
                    keyword, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reddit_post_id) DO UPDATE SET
                    upvotes = EXCLUDED.upvotes,
                    num_comments = EXCLUDED.num_comments,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                post_data['id'],
                post_data.get('subreddit', ''),
                post_data.get('title', ''),
                post_data.get('selftext', ''),
                post_data.get('author', ''),
                post_data.get('created_utc', 0),
                post_data.get('ups', 0),
                post_data.get('num_comments', 0),
                post_data.get('permalink', ''),
                post_data.get('url', ''),
                post_data.get('keyword', ''),
                Json(post_data)
            ))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def upsert_reddit_comment(comment_data: Dict[str, Any], post_id: str, run_id: int) -> bool:
    """Upsert Reddit comment"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO raw_reddit_comments (
                    reddit_comment_id, reddit_post_id, author, body,
                    created_utc, upvotes, is_top, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reddit_comment_id) DO NOTHING
            """, (
                comment_data['id'],
                post_id,
                comment_data.get('author', ''),
                comment_data.get('body', ''),
                comment_data.get('created_utc', 0),
                comment_data.get('ups', 0),
                comment_data.get('is_top', False),
                Json(comment_data)
            ))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def upsert_serp_aio(query: str, aio_data: Dict[str, Any], run_id: int) -> bool:
    """Upsert SERP AI Overview"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO raw_serp_aio (
                    query, locale, snapshot_at, run_id, aio_text,
                    cited_sources_json, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (query, snapshot_at) DO UPDATE SET
                    aio_text = EXCLUDED.aio_text,
                    cited_sources_json = EXCLUDED.cited_sources_json,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                query,
                aio_data.get('locale', 'en-US'),
                datetime.utcnow(),
                run_id,
                aio_data.get('aio_text', ''),
                Json(aio_data.get('cited_sources', [])),
                Json(aio_data)
            ))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def upsert_gsc_query(gsc_data: Dict[str, Any], run_id: int) -> bool:
    """Upsert GSC query data"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Parse date_month from date
            from datetime import datetime as dt
            date_str = gsc_data.get('date', '')
            if date_str:
                date_obj = dt.strptime(date_str, '%Y-%m-%d')
                date_month = date_obj.replace(day=1).date()
            else:
                date_month = datetime.utcnow().date().replace(day=1)
            
            cur.execute("""
                INSERT INTO raw_gsc_queries (
                    query, page, country, device, date_month,
                    impressions, clicks, ctr, position, raw_row_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (query, page, country, device, date_month) DO UPDATE SET
                    impressions = EXCLUDED.impressions,
                    clicks = EXCLUDED.clicks,
                    ctr = EXCLUDED.ctr,
                    position = EXCLUDED.position,
                    raw_row_json = EXCLUDED.raw_row_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                gsc_data.get('query', ''),
                gsc_data.get('page', ''),
                gsc_data.get('country', 'usa'),
                gsc_data.get('device', 'desktop'),
                date_month,
                int(gsc_data.get('impressions', 0)),
                int(gsc_data.get('clicks', 0)),
                float(gsc_data.get('ctr', 0)),
                float(gsc_data.get('position', 0)) if gsc_data.get('position') else None,
                Json(gsc_data)
            ))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def upsert_embedding(doc_type: str, doc_id: str, embedding: List[float], 
                     text_hash: str, model_name: str, dim: int, run_id: int) -> bool:
    """Upsert embedding"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO embeddings (
                    doc_type, doc_id, text_hash, embedding_json,
                    model_name, dim, created_from_run_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_type, doc_id, created_from_run_id) DO UPDATE SET
                    embedding_json = EXCLUDED.embedding_json,
                    text_hash = EXCLUDED.text_hash,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                doc_type, doc_id, text_hash, Json(embedding),
                model_name, dim, run_id
            ))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def upsert_cluster_assignment(cluster_id: int, doc_type: str, doc_id: str,
                              distance: float, is_representative: bool, run_id: int) -> bool:
    """Upsert cluster assignment"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cluster_assignments (
                    cluster_id, doc_type, doc_id, distance_to_centroid,
                    is_representative, created_from_run_id
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_type, doc_id, created_from_run_id) DO UPDATE SET
                    cluster_id = EXCLUDED.cluster_id,
                    distance_to_centroid = EXCLUDED.distance_to_centroid,
                    is_representative = EXCLUDED.is_representative,
                    updated_at = CURRENT_TIMESTAMP
            """, (cluster_id, doc_type, doc_id, distance, is_representative, run_id))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def upsert_topic_qa_brief(brief_data: Dict[str, Any], cluster_id: int, 
                          model_name: str, model_version: str, run_id: int) -> bool:
    """Upsert topic Q&A brief"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO topic_qa_briefs (
                    cluster_id, category, topic_title, primary_question,
                    related_questions_json, blog_angle, social_angle,
                    why_now_json, evidence_pack_json, model_name, model_version,
                    created_from_run_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cluster_id, model_version) DO UPDATE SET
                    category = EXCLUDED.category,
                    topic_title = EXCLUDED.topic_title,
                    primary_question = EXCLUDED.primary_question,
                    related_questions_json = EXCLUDED.related_questions_json,
                    blog_angle = EXCLUDED.blog_angle,
                    social_angle = EXCLUDED.social_angle,
                    why_now_json = EXCLUDED.why_now_json,
                    evidence_pack_json = EXCLUDED.evidence_pack_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                cluster_id,
                brief_data.get('category'),
                brief_data.get('topic_title'),
                brief_data.get('primary_question'),
                Json(brief_data.get('related_questions', [])),
                brief_data.get('blog_angle'),
                brief_data.get('social_angle'),
                Json(brief_data.get('why_now', {})),
                Json(brief_data.get('evidence_pack', {})),
                model_name,
                model_version,
                run_id
            ))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
