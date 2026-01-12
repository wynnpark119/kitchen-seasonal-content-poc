"""
Embedding generation using OpenAI text-embedding-3-large

배치 처리 및 retry/backoff 지원
pgvector 자동 감지 및 분기 처리
"""
import os
import time
import json
from typing import List, Dict, Any, Tuple, Optional, Set
from openai import OpenAI
from .config import (
    EMBEDDING_MODEL, EMBEDDING_DIM, API_MAX_RETRIES, API_BACKOFF_FACTOR, 
    EMBEDDING_BATCH_SIZE, DB_WRITE_CONCURRENCY, DB_BATCH_SIZE
)
from .db import get_db_connection, put_db_connection, upsert_embeddings_batch, check_pgvector_available
from .preprocess import build_analysis_text, get_text_hash, is_deleted_post
from .logging import setup_logger
import threading
from psycopg2.extras import Json as PsycopgJson

logger = setup_logger("embedding")

# DB write 동시성 제한 (Semaphore)
db_write_semaphore = threading.Semaphore(DB_WRITE_CONCURRENCY)

# Maximum tokens for text-embedding-3-large
MAX_TOKENS = 8192

def truncate_text_to_max_tokens(text: str, max_tokens: int = MAX_TOKENS) -> str:
    """
    텍스트를 최대 토큰 수로 자르기
    
    Args:
        text: 원본 텍스트
        max_tokens: 최대 토큰 수
    
    Returns:
        잘린 텍스트
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model("text-embedding-3-large")
        tokens = encoding.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        # 토큰을 자르고 다시 디코딩
        truncated_tokens = tokens[:max_tokens]
        truncated_text = encoding.decode(truncated_tokens)
        logger.warning(f"Text truncated from {len(tokens)} tokens to {max_tokens} tokens")
        return truncated_text
    except ImportError:
        # tiktoken이 없으면 문자 수로 대략 추정 (1 토큰 ≈ 4 문자)
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        logger.warning(f"tiktoken not available, truncating by character count: {len(text)} -> {max_chars}")
        return text[:max_chars]
    except Exception as e:
        logger.warning(f"Error truncating text: {e}, using character-based truncation")
        # Fallback: 문자 수로 자르기
        max_chars = max_tokens * 4
        return text[:max_chars] if len(text) > max_chars else text

def generate_embeddings_batch(texts: List[str], client: OpenAI) -> List[List[float]]:
    """
    배치로 임베딩 생성 (retry/backoff 포함)
    
    Args:
        texts: 텍스트 리스트
        client: OpenAI client
    
    Returns:
        임베딩 리스트
    """
    for attempt in range(API_MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            if attempt < API_MAX_RETRIES - 1:
                wait_time = API_BACKOFF_FACTOR ** attempt
                logger.warning(f"Batch embedding generation failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise

def check_existing_hashes_batch(text_hashes: List[str], run_id: int) -> Set[str]:
    """
    배치로 중복 해시 체크 (한 커넥션으로 처리)
    
    Args:
        text_hashes: 체크할 해시 리스트
        run_id: Pipeline run ID
    
    Returns:
        이미 존재하는 해시 집합
    """
    if not text_hashes:
        return set()
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT text_hash 
                FROM embeddings 
                WHERE text_hash = ANY(%s)
            """, (text_hashes,))
            existing = set(row[0] for row in cur.fetchall())
            return existing
    finally:
        if conn:
            put_db_connection(conn)

def generate_embeddings(run_id: int, dry_run: bool = False, 
                        batch_size: int = EMBEDDING_BATCH_SIZE,
                        max_docs: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate embeddings for Reddit posts
    
    ✅ 개선사항:
    - 함수 시작 시 커넥션 획득 제거
    - 필요한 시점에만 커넥션 획득 및 즉시 반납
    - 중복 체크 배치 처리
    - DB write 동시성 제한
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
        batch_size: Batch size for embedding generation
        max_docs: Maximum documents to process (for cost control, None = all)
    
    Returns:
        Statistics dictionary
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key and not dry_run:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    if not dry_run:
        client = OpenAI(api_key=openai_key)
    
    # pgvector 사용 가능 여부 확인
    use_pgvector = check_pgvector_available()
    logger.info(f"pgvector available: {use_pgvector} (using {'vector' if use_pgvector else 'JSONB'} storage)")
    
    stats = {
        "posts_processed": 0,
        "embeddings_created": 0,
        "batches_processed": 0,
        "skipped_existing": 0,
        "errors": []
    }
    
    # ✅ 1. 포스트 목록 조회 (짧은 트랜잭션, 즉시 반납)
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT rp.reddit_post_id, rp.title, rp.body
                    FROM raw_reddit_posts rp
                    WHERE NOT EXISTS (
                        SELECT 1 FROM embeddings e
                        WHERE e.doc_type = 'reddit_post'
                        AND e.doc_id = rp.reddit_post_id
                        AND e.created_from_run_id = %s
                    )
                    AND rp.title IS NOT NULL
                    AND LENGTH(COALESCE(rp.title, '')) > 0
                    ORDER BY rp.upvotes DESC, rp.num_comments DESC
                """
                
                if max_docs:
                    query += f" LIMIT {max_docs}"
                
                cur.execute(query, (run_id,))
                all_posts = cur.fetchall()
                stats["posts_processed"] = len(all_posts)
                total_posts = len(all_posts)
        finally:
            put_db_connection(conn)  # ✅ 즉시 반납
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        stats["errors"].append(str(e))
        return stats
    
    logger.info(f"Generating embeddings for {total_posts} posts (batch_size={batch_size})")
    
    # ✅ 2. 텍스트 전처리 및 해시 생성 (DB 커넥션 없음)
    posts_to_process = []
    for post_id, title, body in all_posts:
        try:
            # 삭제된 글 스킵
            if is_deleted_post(title, body):
                continue
            
            # 분석용 텍스트 생성
            analysis_text = build_analysis_text(title, body)
            
            # 너무 짧은 글 스킵 (30자 이하)
            if len(analysis_text) < 30:
                continue
            
            # 토큰 수 제한 적용 (8192 토큰)
            analysis_text = truncate_text_to_max_tokens(analysis_text, MAX_TOKENS)
            
            # text_hash 생성
            text_hash = get_text_hash(analysis_text)
            
            posts_to_process.append((post_id, analysis_text, text_hash))
        except Exception as e:
            logger.error(f"Error preprocessing post {post_id}: {e}")
            stats["errors"].append(str(e))
    
    # ✅ 3. 중복 체크 배치 처리 (한 번에 처리)
    if posts_to_process and not dry_run:
        text_hashes_to_check = [text_hash for _, _, text_hash in posts_to_process]
        existing_hashes = check_existing_hashes_batch(text_hashes_to_check, run_id)
        
        # 중복 제거
        posts_to_process = [
            (post_id, text, hash_val) 
            for post_id, text, hash_val in posts_to_process
            if hash_val not in existing_hashes
        ]
        stats["skipped_existing"] = len(text_hashes_to_check) - len(posts_to_process)
    
    logger.info(f"Processing {len(posts_to_process)} posts (skipped {stats['skipped_existing']} existing)")
    
    # ✅ 4. 배치 처리: API 호출 → DB 저장 (커넥션 분리)
    batch = []
    batch_post_ids = []
    batch_text_hashes = []
    processed_count = 0
    
    for post_id, analysis_text, text_hash in posts_to_process:
        batch.append(analysis_text)
        batch_post_ids.append(post_id)
        batch_text_hashes.append(text_hash)
        
        # 배치가 가득 차면 처리
        if len(batch) >= batch_size:
            if dry_run:
                logger.info(f"[DRY RUN] Would generate embeddings for batch of {len(batch)} posts")
                stats["embeddings_created"] += len(batch)
                stats["batches_processed"] += 1
            else:
                # ✅ API 호출 (DB 커넥션 없음)
                batch_start_time = time.time()
                embeddings = generate_embeddings_batch(batch, client)
                api_time = time.time() - batch_start_time
                
                # ✅ DB 저장 (동시성 제한, 짧은 트랜잭션)
                db_save_start = time.time()
                with db_write_semaphore:  # 동시성 제한
                    embeddings_data = [
                        ("reddit_post", post_id, embedding, text_hash, EMBEDDING_MODEL, EMBEDDING_DIM, run_id)
                        for post_id, text_hash, embedding in zip(batch_post_ids, batch_text_hashes, embeddings)
                    ]
                    upsert_embeddings_batch(embeddings_data, run_id)
                db_save_time = time.time() - db_save_start
                
                processed_count += len(batch)
                stats["embeddings_created"] += len(batch)
                stats["batches_processed"] += 1
                batch_time = time.time() - batch_start_time
                
                # 진행 상황 출력
                progress_pct = (processed_count / len(posts_to_process) * 100) if posts_to_process else 0
                logger.info(f"[PROGRESS] Batch {stats['batches_processed']}: {len(batch)} posts processed | "
                          f"Total: {processed_count}/{len(posts_to_process)} ({progress_pct:.1f}%) | "
                          f"API: {api_time:.2f}s | "
                          f"DB: {db_save_time:.2f}s | "
                          f"Rate: {len(batch)/batch_time:.1f} posts/s")
                
                # Rate limiting
                time.sleep(0.1)
            
            # 배치 초기화
            batch = []
            batch_post_ids = []
            batch_text_hashes = []
    
    # ✅ 5. 남은 배치 처리
    if batch:
        if dry_run:
            logger.info(f"[DRY RUN] Would generate embeddings for final batch of {len(batch)} posts")
            stats["embeddings_created"] += len(batch)
            stats["batches_processed"] += 1
        else:
            # ✅ API 호출 (DB 커넥션 없음)
            batch_start_time = time.time()
            embeddings = generate_embeddings_batch(batch, client)
            api_time = time.time() - batch_start_time
            
            # ✅ DB 저장 (동시성 제한, 짧은 트랜잭션)
            db_save_start = time.time()
            with db_write_semaphore:  # 동시성 제한
                embeddings_data = [
                    ("reddit_post", post_id, embedding, text_hash, EMBEDDING_MODEL, EMBEDDING_DIM, run_id)
                    for post_id, text_hash, embedding in zip(batch_post_ids, batch_text_hashes, embeddings)
                ]
                upsert_embeddings_batch(embeddings_data, run_id)
            db_save_time = time.time() - db_save_start
            
            processed_count += len(batch)
            stats["embeddings_created"] += len(batch)
            stats["batches_processed"] += 1
            batch_time = time.time() - batch_start_time
            
            # 최종 배치 진행 상황 출력
            progress_pct = (processed_count / len(posts_to_process) * 100) if posts_to_process else 0
            logger.info(f"[PROGRESS] Final batch {stats['batches_processed']}: {len(batch)} posts processed | "
                      f"Total: {processed_count}/{len(posts_to_process)} ({progress_pct:.1f}%) | "
                      f"API: {api_time:.2f}s | DB: {db_save_time:.2f}s | "
                      f"Time: {batch_time:.2f}s")
    
    logger.info(f"Embedding generation completed:")
    logger.info(f"  Posts processed: {stats['posts_processed']}")
    logger.info(f"  Embeddings created: {stats['embeddings_created']}")
    logger.info(f"  Skipped (existing): {stats['skipped_existing']}")
    logger.info(f"  Batches processed: {stats['batches_processed']}")
    
    return stats
