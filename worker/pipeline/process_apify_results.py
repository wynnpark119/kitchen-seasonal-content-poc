"""
Process Apify MCP results and save to database
"""
import json
import time
from typing import List, Dict, Any
from .db import upsert_reddit_post, upsert_reddit_comment, get_db_connection
from .logging import setup_logger

logger = setup_logger("process_apify_results")

def process_apify_results(items: List[Dict[str, Any]], keyword: str, run_id: int) -> Dict[str, Any]:
    """Process Apify MCP results and save to database"""
    from .logging import setup_logger
    from .db import upsert_reddit_posts_batch
    logger = setup_logger("process_apify_results")
    
    stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "errors": []
    }
    
    posts_to_insert = []
    comments_to_insert = []
    
    logger.info(f"Processing {len(items)} items for keyword: {keyword}")
    
    # 진행률 로깅을 위한 카운터
    processed_count = 0
    posts_count = 0
    comments_count = 0
    progress_interval = max(50, len(items) // 20)  # 최소 50개 또는 전체의 5%마다
    
    start_time = time.time()
    logger.info(f"[PROCESS] Starting processing at {time.strftime('%H:%M:%S')}")
    
    for idx, item in enumerate(items, 1):
        processed_count = idx
        
        # 진행률 로그 (N건마다)
        if idx % progress_interval == 0 or idx == len(items):
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            logger.info(f"[PROCESS] Progress: {idx}/{len(items)} ({idx*100//len(items)}%) | "
                       f"Posts: {posts_count}, Comments: {comments_count} | "
                       f"Elapsed: {elapsed:.1f}s | Rate: {rate:.1f} items/s")
        try:
            # Support both harshmaur (dataType) and fatihtahta (kind) formats
            data_type = item.get('dataType') or item.get('kind', 'post')
            
            if data_type == 'post':
                # Process post
                post_id = item.get('parsedId') or item.get('id', '')
                # 검증 강화: 빈 문자열, None, 공백만 있는 경우 제외
                if not post_id or not isinstance(post_id, str) or len(str(post_id).strip()) == 0:
                    logger.debug(f"Skipping post with invalid ID: {item.get('id', 'unknown')}")
                    continue
                
                post_id = str(post_id).strip()
                
                # Extract subreddit name (support both formats)
                subreddit = item.get('subredditName') or item.get('subreddit', '')
                if not subreddit:
                    community = item.get('communityName', '')
                    if community:
                        subreddit = community.replace('r/', '')
                
                # Support both timestamp formats
                created_utc_str = item.get('createdAt') or item.get('created_utc', '')
                created_utc = _parse_timestamp(created_utc_str)
                if created_utc <= 0:
                    import time
                    created_utc = int(time.time())
                    logger.debug(f"Post {post_id} has invalid timestamp, using current time")
                
                post_data = {
                    'id': post_id,
                    'subreddit': subreddit or 'unknown',
                    'title': item.get('title', '') or 'Untitled',
                    'selftext': item.get('body') or item.get('text') or item.get('selftext', '') or '',
                    'author': item.get('authorName') or item.get('author', '') or '',
                    'created_utc': created_utc,
                    'ups': item.get('upVotes') or item.get('upvotes') or item.get('score', 0),
                    'num_comments': item.get('commentsCount') or item.get('num_comments', 0),
                    'permalink': item.get('postUrl') or item.get('permalink') or item.get('url', '') or '',
                    'url': item.get('contentUrl') or item.get('postUrl') or item.get('url', '') or '',
                    'keyword': keyword
                }
                
                posts_to_insert.append(post_data)
                posts_count += 1
                
            elif data_type == 'comment':
                # Process comment
                comment_id = item.get('id', '')
                post_id = item.get('parsedPostId') or item.get('postId', '')
                
                # 검증 강화
                if not comment_id or not post_id:
                    continue
                comment_id = str(comment_id).strip()
                post_id = str(post_id).strip()
                if not comment_id or not post_id:
                    continue
                
                # Support both timestamp formats
                created_utc_str = item.get('commentCreatedAt') or item.get('createdAt') or item.get('created_utc', '')
                created_utc = _parse_timestamp(created_utc_str)
                if created_utc <= 0:
                    import time
                    created_utc = int(time.time())
                
                comment_data = {
                    'id': comment_id,
                    'body': item.get('body') or item.get('text', '') or '',
                    'author': item.get('authorName') or item.get('author', '') or '',
                    'created_utc': created_utc,
                    'ups': item.get('commentUpVotes') or item.get('upvotes') or item.get('score', 0),
                    'is_top': False,
                    'post_id': post_id  # 배치 처리용
                }
                
                comments_to_insert.append(comment_data)
                comments_count += 1
                
        except Exception as e:
            logger.error(f"[PROCESS] Error at item {idx}/{len(items)} (id: {item.get('id', 'unknown')}): {e}")
            logger.error(f"Error processing item {item.get('id', 'unknown')}: {e}", exc_info=True)
            stats["errors"].append(str(e))
    
    # 배치로 포스트 저장
    processing_elapsed = time.time() - start_time
    logger.info(f"[PROCESS] Processing completed: {processed_count} items in {processing_elapsed:.2f}s")
    logger.info(f"[PROCESS] Prepared: {len(posts_to_insert)} posts, {len(comments_to_insert)} comments")
    
    try:
        if posts_to_insert:
            batch_start = time.time()
            logger.info(f"[BATCH] Starting batch insert: {len(posts_to_insert)} posts...")
            batch_stats = upsert_reddit_posts_batch(posts_to_insert, run_id)
            batch_elapsed = time.time() - batch_start
            stats["posts_collected"] = batch_stats.get("inserted", 0)
            logger.info(f"[BATCH] Batch insert completed: {stats['posts_collected']} posts in {batch_elapsed:.2f}s")
            if batch_stats.get("errors", 0) > 0:
                stats["errors"].extend([f"Batch error for {batch_stats['errors']} posts"])
    except Exception as e:
        batch_elapsed = time.time() - batch_start if 'batch_start' in locals() else 0
        logger.error(f"[BATCH] ❌ Batch insert error after {batch_elapsed:.2f}s: {e}", exc_info=True)
        stats["errors"].append(f"Batch insert failed: {str(e)}")
    
    # 댓글 저장 (개별 처리, 배치는 추후 개선 가능)
    for comment_data in comments_to_insert:
        try:
            from .db import upsert_reddit_comment
            upsert_reddit_comment(comment_data, comment_data['post_id'], run_id)
            stats["comments_collected"] += 1
        except Exception as e:
            logger.error(f"Error inserting comment {comment_data.get('id', 'unknown')}: {e}")
            stats["errors"].append(str(e))
    
    logger.info(f"Processed: {stats['posts_collected']} posts, {stats['comments_collected']} comments, {len(stats['errors'])} errors")
    return stats

def _parse_timestamp(timestamp_str: str) -> int:
    """Parse ISO timestamp to Unix timestamp"""
    if not timestamp_str:
        return 0
    
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except:
        return 0
