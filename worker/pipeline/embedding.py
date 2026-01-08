"""
Embedding generation using OpenAI
"""
import os
import time
from typing import List, Dict, Any
from openai import OpenAI
from .config import EMBEDDING_MODEL, EMBEDDING_DIM, API_MAX_RETRIES, API_BACKOFF_FACTOR
from .db import get_db_connection, upsert_embedding
from .preprocess import clean_text, get_text_hash as hash_text
from .logging import setup_logger

logger = setup_logger("embedding")

def generate_embedding(text: str, client: OpenAI) -> List[float]:
    """Generate embedding for text with retry logic"""
    for attempt in range(API_MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            if attempt < API_MAX_RETRIES - 1:
                wait_time = API_BACKOFF_FACTOR ** attempt
                logger.warning(f"Embedding generation failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise

def generate_embeddings(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Generate embeddings for Reddit posts"""
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    client = OpenAI(api_key=openai_key)
    
    conn = get_db_connection()
    stats = {
        "posts_processed": 0,
        "embeddings_created": 0,
        "errors": []
    }
    
    try:
        with conn.cursor() as cur:
            # Get posts that don't have embeddings for this run
            cur.execute("""
                SELECT rp.reddit_post_id, rp.title, rp.body
                FROM raw_reddit_posts rp
                WHERE NOT EXISTS (
                    SELECT 1 FROM embeddings e
                    WHERE e.doc_type = 'reddit_post'
                    AND e.doc_id = rp.reddit_post_id
                    AND e.created_from_run_id = %s
                )
                ORDER BY rp.created_utc DESC
                LIMIT 1000
            """, (run_id,))
            
            posts = cur.fetchall()
            stats["posts_processed"] = len(posts)
            
            logger.info(f"Generating embeddings for {stats['posts_processed']} posts")
            
            for post_id, title, body in posts:
                try:
                    # Combine title and body
                    combined_text = f"{clean_text(title or '')} {clean_text(body or '')}"
                    text_hash = hash_text(combined_text)
                    
                    if dry_run:
                        if stats["embeddings_created"] < 3:
                            logger.info(f"[DRY RUN] Would generate embedding for post: {title[:50]}...")
                        stats["embeddings_created"] += 1
                        continue
                    
                    # Generate embedding
                    embedding = generate_embedding(combined_text, client)
                    
                    # Store embedding
                    upsert_embedding(
                        doc_type="reddit_post",
                        doc_id=post_id,
                        embedding=embedding,
                        text_hash=text_hash,
                        model_name=EMBEDDING_MODEL,
                        dim=EMBEDDING_DIM,
                        run_id=run_id
                    )
                    
                    stats["embeddings_created"] += 1
                    
                    # Rate limiting
                    time.sleep(0.1)
                
                except Exception as e:
                    logger.error(f"Error generating embedding for post {post_id}: {e}")
                    stats["errors"].append(str(e))
    
    finally:
        conn.close()
    
    logger.info(f"Embedding generation completed: {stats['embeddings_created']} embeddings created")
    return stats
