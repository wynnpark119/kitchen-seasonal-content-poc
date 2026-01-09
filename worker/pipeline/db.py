"""
Database connection and helper functions

pgvector 자동 감지 및 분기 처리 포함
"""
import psycopg2
import json
from psycopg2.extras import execute_values, execute_batch, Json
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import pool
from typing import Optional, Dict, Any, List
import os
import threading
import time
from functools import wraps
from datetime import datetime
from .logging import setup_logger

logger = setup_logger("db")

# pgvector 사용 가능 여부 캐시
_pgvector_available = None

# Connection pool
_connection_pool = None
_pool_lock = threading.Lock()

def get_connection_pool():
    """Get or create connection pool"""
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                database_url = (
                    os.getenv("DATABASE_URL") or 
                    os.getenv("RAILWAY_DATABASE_URL") or
                    os.getenv("POSTGRES_URL") or
                    os.getenv("POSTGRES_PRIVATE_URL")
                )
                if not database_url:
                    raise ValueError("DATABASE_URL not found in environment variables")
                
                # Railway PostgreSQL SSL 설정 강화
                # Railway URL 패턴: *.railway.app, *.proxy.rlwy.net, *.up.railway.app
                is_railway = any(pattern in database_url.lower() for pattern in [
                    'railway.app', 'rlwy.net', 'up.railway.app'
                ])
                
                if is_railway:
                    # SSL 모드 확인 및 추가
                    if 'sslmode' not in database_url.lower():
                        separator = '&' if '?' in database_url else '?'
                        database_url = f"{database_url}{separator}sslmode=require"
                        logger.info("Added sslmode=require to Railway database URL")
                    elif 'sslmode=disable' in database_url.lower():
                        # sslmode=disable이면 require로 변경
                        database_url = database_url.replace('sslmode=disable', 'sslmode=require')
                        logger.warning("Changed sslmode from disable to require for Railway")
                
                # 연결 테스트를 위한 로그 (민감 정보 마스킹)
                url_masked = database_url.split('@')[-1] if '@' in database_url else database_url[:50]
                logger.info(f"Connecting to database: ...@{url_masked}")
                logger.debug(f"SSL mode: {'sslmode' in database_url.lower()}")
                
                try:
                    # Connection pool 생성 (min 2, max 10)
                    _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=2,
                        maxconn=10,
                        dsn=database_url,
                        connect_timeout=10  # 연결 타임아웃 10초
                    )
                    logger.info("Connection pool created successfully")
                except Exception as e:
                    logger.error(f"Failed to create connection pool: {e}")
                    logger.error(f"Database URL pattern: {url_masked}")
                    raise
    return _connection_pool

def get_db_connection():
    """Get database connection from pool"""
    try:
        pool = get_connection_pool()
        conn = pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e}")
        # Fallback: 직접 연결 (SSL 설정 포함)
        database_url = (
            os.getenv("DATABASE_URL") or 
            os.getenv("RAILWAY_DATABASE_URL") or
            os.getenv("POSTGRES_URL") or
            os.getenv("POSTGRES_PRIVATE_URL")
        )
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        # Railway SSL 설정 (fallback에도 적용)
        is_railway = any(pattern in database_url.lower() for pattern in [
            'railway.app', 'rlwy.net', 'up.railway.app'
        ])
        if is_railway and 'sslmode' not in database_url.lower():
            separator = '&' if '?' in database_url else '?'
            database_url = f"{database_url}{separator}sslmode=require"
        
        return psycopg2.connect(database_url, connect_timeout=10)

def put_db_connection(conn):
    """Return connection to pool"""
    try:
        pool = get_connection_pool()
        pool.putconn(conn)
    except Exception as e:
        logger.warning(f"Failed to return connection to pool: {e}")
        try:
            conn.close()
        except:
            pass

def retry_db_operation(max_retries=3, backoff=1.0):
    """데이터베이스 작업 재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff * (2 ** attempt)
                        logger.warning(f"DB operation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"DB operation failed after {max_retries} attempts: {e}")
                        raise
                except Exception as e:
                    # 재시도하지 않는 에러는 즉시 raise
                    raise
            raise last_exception
        return wrapper
    return decorator

def check_pgvector_available() -> bool:
    """
    pgvector extension 사용 가능 여부 확인
    
    Returns:
        True if pgvector is available, False otherwise
    """
    global _pgvector_available
    if _pgvector_available is not None:
        return _pgvector_available
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if vector type exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'vector'
                )
            """)
            _pgvector_available = cur.fetchone()[0]
            return _pgvector_available
    except Exception as e:
        # If check fails, assume pgvector is not available
        _pgvector_available = False
        return False
    finally:
        conn.close()

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

@retry_db_operation(max_retries=3, backoff=1.0)
def update_pipeline_run(run_id: int, status: str, error_message: Optional[str] = None, metadata: Optional[Dict] = None):
    """Update pipeline run status"""
    conn = None
    try:
        conn = get_db_connection()
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
        if conn:
            put_db_connection(conn)

@retry_db_operation(max_retries=3, backoff=1.0)
def upsert_reddit_post(post_data: Dict[str, Any], run_id: int) -> bool:
    """Upsert Reddit post (insert or update if exists)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 데이터 검증 및 정규화
            post_id = str(post_data.get('id', '')).strip()
            if not post_id:
                raise ValueError("post_data['id'] is required and cannot be empty")
            
            created_utc = post_data.get('created_utc', 0)
            if not isinstance(created_utc, int) or created_utc <= 0:
                import time
                created_utc = int(time.time())
                logger.warning(f"Invalid created_utc for post {post_id}, using current time")
            
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
                post_id,
                (post_data.get('subreddit', '') or 'unknown')[:100],
                (post_data.get('title', '') or 'Untitled')[:10000],
                (post_data.get('selftext', '') or '')[:50000] or None,
                (post_data.get('author', '') or '')[:100] or None,
                created_utc,
                max(0, int(post_data.get('ups', 0))),
                max(0, int(post_data.get('num_comments', 0))),
                (post_data.get('permalink', '') or '')[:5000] or None,
                (post_data.get('url', '') or '')[:5000] or None,
                (post_data.get('keyword', '') or '')[:200],
                Json(post_data)
            ))
            conn.commit()
            return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error upserting post {post_data.get('id', 'unknown')}: {e}")
        raise e
    finally:
        if conn:
            put_db_connection(conn)

def upsert_reddit_posts_batch(posts_data: List[Dict[str, Any]], run_id: int) -> Dict[str, int]:
    """Batch upsert Reddit posts (성능 개선)"""
    if not posts_data:
        return {"inserted": 0, "updated": 0, "errors": 0}
    
    # 배치 크기 제한 (한 번에 최대 500개)
    BATCH_SIZE_LIMIT = 500
    if len(posts_data) > BATCH_SIZE_LIMIT:
        logger.warning(f"Batch size {len(posts_data)} exceeds limit {BATCH_SIZE_LIMIT}, splitting...")
        # 재귀적으로 분할 처리
        stats = {"inserted": 0, "updated": 0, "errors": 0}
        for i in range(0, len(posts_data), BATCH_SIZE_LIMIT):
            batch = posts_data[i:i + BATCH_SIZE_LIMIT]
            batch_stats = upsert_reddit_posts_batch(batch, run_id)
            stats["inserted"] += batch_stats["inserted"]
            stats["updated"] += batch_stats["updated"]
            stats["errors"] += batch_stats["errors"]
        return stats
    
    conn = None
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    
    @retry_db_operation(max_retries=3, backoff=2.0)
    def _execute_batch_insert(insert_data):
        nonlocal conn, stats
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # 배치 INSERT
            execute_batch(cur, """
                INSERT INTO raw_reddit_posts (
                    reddit_post_id, subreddit, title, body, author,
                    created_utc, upvotes, num_comments, permalink, url,
                    keyword, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reddit_post_id) DO UPDATE SET
                    upvotes = EXCLUDED.upvotes,
                    num_comments = EXCLUDED.num_comments,
                    updated_at = CURRENT_TIMESTAMP
            """, insert_data, page_size=100)
            
            stats["inserted"] = len(insert_data)
            conn.commit()
            logger.info(f"Batch upserted {stats['inserted']} posts, {stats['errors']} errors")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Batch insert error: {e}", exc_info=True)
            # 첫 번째 실패한 레코드 샘플 로깅
            if insert_data:
                sample = insert_data[0]
                logger.error(f"Sample data (first record): post_id={sample[0]}, "
                           f"title_len={len(sample[2]) if sample[2] else 0}, "
                           f"body_len={len(sample[3]) if sample[3] else 0}")
            raise
    
    try:
        # 배치 처리용 데이터 준비
        insert_data = []
        import time as time_module
        
        for post_data in posts_data:
            try:
                post_id = str(post_data.get('id', '')).strip()
                if not post_id:
                    stats["errors"] += 1
                    continue
                
                created_utc = post_data.get('created_utc', 0)
                if not isinstance(created_utc, int) or created_utc <= 0:
                    created_utc = int(time_module.time())
                
                insert_data.append((
                    post_id,
                    (post_data.get('subreddit', '') or 'unknown')[:100],
                    (post_data.get('title', '') or 'Untitled')[:10000],
                    (post_data.get('selftext', '') or '')[:50000] or None,
                    (post_data.get('author', '') or '')[:100] or None,
                    created_utc,
                    max(0, int(post_data.get('ups', 0))),
                    max(0, int(post_data.get('num_comments', 0))),
                    (post_data.get('permalink', '') or '')[:5000] or None,
                    (post_data.get('url', '') or '')[:5000] or None,
                    (post_data.get('keyword', '') or '')[:200],
                    Json(post_data)
                ))
            except Exception as e:
                logger.error(f"Error preparing post data {post_data.get('id', 'unknown')}: {e}")
                stats["errors"] += 1
                continue
        
        if not insert_data:
            return stats
        
        # 배치 INSERT 실행 (재시도 포함)
        _execute_batch_insert(insert_data)
        
    except Exception as e:
        logger.error(f"Batch upsert error (final): {e}", exc_info=True)
        stats["errors"] = len(posts_data) - stats["inserted"]
        # 부분 성공 허용 (에러를 다시 raise하지 않음)
        # raise  # 주석 처리: 부분 성공 허용
    finally:
        if conn:
            put_db_connection(conn)
    
    return stats

@retry_db_operation(max_retries=3, backoff=1.0)
def upsert_reddit_comment(comment_data: Dict[str, Any], post_id: str, run_id: int) -> bool:
    """Upsert Reddit comment"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 데이터 검증
            comment_id = str(comment_data.get('id', '')).strip()
            post_id_str = str(post_id).strip()
            
            if not comment_id or not post_id_str:
                raise ValueError("comment_id and post_id are required")
            
            created_utc = comment_data.get('created_utc', 0)
            if not isinstance(created_utc, int) or created_utc <= 0:
                import time
                created_utc = int(time.time())
            
            cur.execute("""
                INSERT INTO raw_reddit_comments (
                    reddit_comment_id, reddit_post_id, author, body,
                    created_utc, upvotes, is_top, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reddit_comment_id) DO UPDATE SET
                    upvotes = EXCLUDED.upvotes,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                comment_id,
                post_id_str,
                (comment_data.get('author', '') or '')[:100] or None,
                (comment_data.get('body', '') or '')[:50000],
                created_utc,
                max(0, int(comment_data.get('ups', 0))),
                bool(comment_data.get('is_top', False)),
                Json(comment_data)
            ))
            conn.commit()
            return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error upserting comment {comment_data.get('id', 'unknown')}: {e}")
        raise e
    finally:
        if conn:
            put_db_connection(conn)

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
                    impressions, clicks, ctr, position, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (query, page, country, device, date_month) DO UPDATE SET
                    impressions = EXCLUDED.impressions,
                    clicks = EXCLUDED.clicks,
                    ctr = EXCLUDED.ctr,
                    position = EXCLUDED.position,
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
    """
    Upsert embedding with automatic pgvector/JSONB detection
    
    Args:
        doc_type: Document type (e.g., 'reddit_post')
        doc_id: Document ID
        embedding: Embedding vector (list of floats)
        text_hash: SHA-256 hash of text
        model_name: Model name (e.g., 'text-embedding-3-large')
        dim: Embedding dimension
        run_id: Pipeline run ID
    """
    conn = get_db_connection()
    use_pgvector = check_pgvector_available()
    
    try:
        with conn.cursor() as cur:
            # Use JSONB (pgvector는 현재 사용하지 않음, DDL에서 JSONB로 정의됨)
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
                          model_name: str, model_version: str, run_id: int,
                          insights_json: Optional[Dict[str, Any]] = None) -> bool:
    """
    Upsert topic Q&A brief with insights_json
    
    Args:
        brief_data: Brief data dictionary
        cluster_id: Cluster ID
        model_name: LLM model name
        model_version: Model version
        run_id: Pipeline run ID
        insights_json: Insights module JSON (optional)
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO topic_qa_briefs (
                    cluster_id, category, topic_title, primary_question,
                    related_questions_json, blog_angle, social_angle,
                    why_now_json, evidence_pack_json, insights_json,
                    model_name, model_version, created_from_run_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cluster_id, model_version) DO UPDATE SET
                    category = EXCLUDED.category,
                    topic_title = EXCLUDED.topic_title,
                    primary_question = EXCLUDED.primary_question,
                    related_questions_json = EXCLUDED.related_questions_json,
                    blog_angle = EXCLUDED.blog_angle,
                    social_angle = EXCLUDED.social_angle,
                    why_now_json = EXCLUDED.why_now_json,
                    evidence_pack_json = EXCLUDED.evidence_pack_json,
                    insights_json = EXCLUDED.insights_json,
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
                Json(insights_json) if insights_json else None,
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
