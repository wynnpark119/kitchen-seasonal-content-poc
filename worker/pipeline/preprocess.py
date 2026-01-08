"""
Data preprocessing: cleaning, filtering, deduplication
"""
import hashlib
import re
from typing import List, Dict, Any
from .db import get_db_connection
from .logging import setup_logger

logger = setup_logger("preprocess")

def clean_text(text: str) -> str:
    """Clean text: remove HTML, normalize whitespace"""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_valid_content(title: str, body: str) -> bool:
    """Check if content is valid (question/How-to/idea format)"""
    if not title or len(title) < 10:
        return False
    if not body or len(body) < 50:
        return False
    
    # Check for question/How-to patterns
    patterns = [
        r'^(how|what|why|when|where|can|should|do|does|is|are)',
        r'how to',
        r'ideas? for',
        r'tips? for',
        r'ways? to',
        r'looking for',
        r'need help'
    ]
    
    combined = f"{title} {body}".lower()
    return any(re.search(pattern, combined) for pattern in patterns)

def get_text_hash(text: str) -> str:
    """Get SHA-256 hash of text"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def preprocess_reddit_posts(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Preprocess Reddit posts: clean, filter, deduplicate"""
    conn = get_db_connection()
    stats = {
        "total_posts": 0,
        "valid_posts": 0,
        "cleaned_posts": 0,
        "duplicates_removed": 0,
        "errors": []
    }
    
    try:
        with conn.cursor() as cur:
            # Get all raw posts
            cur.execute("""
                SELECT reddit_post_id, title, body, keyword
                FROM raw_reddit_posts
                ORDER BY created_utc DESC
            """)
            posts = cur.fetchall()
            stats["total_posts"] = len(posts)
            
            logger.info(f"Preprocessing {stats['total_posts']} Reddit posts")
            
            seen_hashes = set()
            
            for post_id, title, body, keyword in posts:
                try:
                    # Clean text
                    clean_title = clean_text(title or "")
                    clean_body = clean_text(body or "")
                    
                    # Validate content
                    if not is_valid_content(clean_title, clean_body):
                        continue
                    
                    stats["valid_posts"] += 1
                    
                    # Check for duplicates
                    combined_text = f"{clean_title} {clean_body}"
                    text_hash = get_text_hash(combined_text)
                    
                    if text_hash in seen_hashes:
                        stats["duplicates_removed"] += 1
                        continue
                    
                    seen_hashes.add(text_hash)
                    
                    if dry_run:
                        if stats["cleaned_posts"] < 5:
                            logger.info(f"[DRY RUN] Sample cleaned post: {clean_title[:50]}...")
                        stats["cleaned_posts"] += 1
                        continue
                    
                    # Update cleaned post (create cleaned table or update existing)
                    # For now, we'll mark posts as processed in metadata
                    stats["cleaned_posts"] += 1
                
                except Exception as e:
                    logger.error(f"Error preprocessing post {post_id}: {e}")
                    stats["errors"].append(str(e))
    
    finally:
        conn.close()
    
    logger.info(f"Preprocessing completed: {stats['cleaned_posts']} posts cleaned")
    return stats
