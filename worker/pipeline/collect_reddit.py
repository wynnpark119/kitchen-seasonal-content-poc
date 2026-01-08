"""
Reddit data collection via Apify (MCP or Direct API)

Note: Apify is connected via MCP. You can use MCP tools to call Actors,
or use ApifyClient directly if APIFY_TOKEN is available.
"""
import os
import time
from typing import List, Dict, Any
from .config import MAX_POSTS_PER_KEYWORD, TOP_COMMENTS_PER_POST, REDDIT_KEYWORDS
from .db import upsert_reddit_post, upsert_reddit_comment
from .logging import setup_logger

logger = setup_logger("collect_reddit")

def collect_reddit_data(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    Collect Reddit posts and comments via Apify
    
    Supports both MCP and direct ApifyClient:
    - If MCP is available, use MCP tools (recommended)
    - Otherwise, fall back to ApifyClient with APIFY_TOKEN
    """
    # Apify connection: MCP or Direct API
    # Note: MCP is connected, but Python code uses ApifyClient for now
    # MCP integration can be added later if needed for direct MCP tool calls
    apify_token = os.getenv("APIFY_TOKEN")
    
    if not apify_token:
        raise ValueError("APIFY_TOKEN not found in environment variables. "
                        "Note: MCP is connected, but ApifyClient still requires APIFY_TOKEN for direct API calls.")
    
    try:
        from apify_client import ApifyClient
        client = ApifyClient(apify_token)
    except ImportError:
        raise ImportError("apify-client not installed. Install with: pip install apify-client")
    
    stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "keywords_processed": 0,
        "errors": []
    }
    
    # Collect from all categories
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        all_keywords.extend(keywords)
    
    logger.info(f"Starting Reddit collection for {len(all_keywords)} keywords")
    
    for keyword in all_keywords:
        try:
            logger.info(f"Collecting Reddit data for keyword: {keyword}")
            
            if dry_run:
                logger.info(f"[DRY RUN] Would collect up to {MAX_POSTS_PER_KEYWORD} posts for '{keyword}'")
                stats["keywords_processed"] += 1
                continue
            
            # Run Apify actor for Reddit search
            # Recommended Actor: harshmaur/reddit-scraper (MCP compatible, pay-per-result)
            # Alternative: fatihtahta/reddit-scraper-search-fast (fast, $1.5/1K results)
            actor_id = os.getenv("APIFY_REDDIT_ACTOR", "harshmaur/reddit-scraper")
            
            # Input schema for harshmaur/reddit-scraper
            run = client.actor(actor_id).call(
                run_input={
                    "searchTerms": [keyword],  # Search query array
                    "searchPosts": True,  # Get posts
                    "searchComments": False,  # Comments will be crawled per post
                    "searchCommunities": False,  # Don't search communities
                    "searchSort": "top",  # Sort by: relevance, hot, top, new, comments
                    "searchTime": "all",  # Time range: all, hour, day, week, month, year
                    "includeNSFW": False,  # Exclude NSFW content
                    "maxPostsCount": MAX_POSTS_PER_KEYWORD,
                    "maxCommentsPerPost": TOP_COMMENTS_PER_POST,
                    "crawlCommentsPerPost": True,  # Crawl comments for each post
                    "fastMode": True,  # Fast mode enabled (less accurate for search, but faster)
                    "proxy": {
                        "useApifyProxy": True,
                        "apifyProxyGroups": ["RESIDENTIAL"]
                    }
                }
            )
            
            # Get results from dataset
            dataset = client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())
            
            logger.info(f"Collected {len(items)} items for keyword '{keyword}'")
            
            for item in items:
                try:
                    # Check if item is a post or comment
                    item_type = item.get('type', 'post')
                    
                    if item_type == 'post' or 'title' in item:
                        # This is a post
                        post = item
                        post['keyword'] = keyword
                        
                        # Map fields to our schema
                        post_data = {
                            'id': post.get('id') or post.get('postId') or f"post_{post.get('url', '')}",
                            'subreddit': post.get('subreddit', ''),
                            'title': post.get('title', ''),
                            'selftext': post.get('text') or post.get('body') or post.get('selftext', ''),
                            'author': post.get('author') or post.get('authorName', ''),
                            'created_utc': post.get('createdAt') or post.get('created', 0),
                            'ups': post.get('upvotes') or post.get('score', 0),
                            'num_comments': post.get('commentsCount') or post.get('numComments', 0),
                            'permalink': post.get('permalink') or post.get('url', ''),
                            'url': post.get('url') or post.get('postUrl', ''),
                            'keyword': keyword
                        }
                        
                        upsert_reddit_post(post_data, run_id)
                        stats["posts_collected"] += 1
                        
                        # Get top comments from the post
                        if 'comments' in post and isinstance(post['comments'], list):
                            comments = sorted(
                                post['comments'],
                                key=lambda x: x.get('upvotes') or x.get('ups') or x.get('score', 0),
                                reverse=True
                            )[:TOP_COMMENTS_PER_POST]
                            
                            for comment in comments:
                                comment_data = {
                                    'id': comment.get('id') or comment.get('commentId', ''),
                                    'body': comment.get('text') or comment.get('body', ''),
                                    'author': comment.get('author') or comment.get('authorName', ''),
                                    'created_utc': comment.get('createdAt') or comment.get('created', 0),
                                    'ups': comment.get('upvotes') or comment.get('ups') or comment.get('score', 0),
                                    'is_top': True
                                }
                                
                                if comment_data['id']:
                                    upsert_reddit_comment(comment_data, post_data['id'], run_id)
                                    stats["comments_collected"] += 1
                    
                    elif item_type == 'comment':
                        # This is a standalone comment (from comment search)
                        comment = item
                        # Comments are typically associated with posts, so we need post_id
                        post_id = comment.get('postId') or comment.get('post_id', '')
                        if post_id:
                            comment_data = {
                                'id': comment.get('id') or comment.get('commentId', ''),
                                'body': comment.get('text') or comment.get('body', ''),
                                'author': comment.get('author') or comment.get('authorName', ''),
                                'created_utc': comment.get('createdAt') or comment.get('created', 0),
                                'ups': comment.get('upvotes') or comment.get('ups') or comment.get('score', 0),
                                'is_top': False
                            }
                            
                            if comment_data['id']:
                                upsert_reddit_comment(comment_data, post_id, run_id)
                                stats["comments_collected"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing item {item.get('id', 'unknown')}: {e}")
                    stats["errors"].append(str(e))
            
            stats["keywords_processed"] += 1
            
            # Rate limiting
            time.sleep(2)
        
        except Exception as e:
            logger.error(f"Error collecting data for keyword '{keyword}': {e}")
            stats["errors"].append(str(e))
    
    logger.info(f"Reddit collection completed: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
    return stats
