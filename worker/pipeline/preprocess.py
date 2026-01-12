"""
Data preprocessing: cleaning, filtering, deduplication

분석용 텍스트 생성 규칙:
- text = title + "\n\n" + body (body 없으면 title만)
- 제거: 너무 짧은 글(30자 이하), 삭제된 글
- 중복: text_hash(sha256)로 동일 텍스트 중복 제거
- 중복 시: upvotes + num_comments 높은 것 우선
"""
import hashlib
import re
from typing import List, Dict, Any, Set, Optional
from .db import get_db_connection
from .config import MIN_TEXT_LENGTH
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

def build_analysis_text(title: str, body: str) -> str:
    """
    분석용 텍스트 생성 규칙:
    text = title + "\n\n" + body (body 없으면 title만)
    """
    clean_title = clean_text(title or "")
    clean_body = clean_text(body or "")
    
    if clean_body:
        return f"{clean_title}\n\n{clean_body}"
    else:
        return clean_title

def build_safe_embedding_text(
    title: str,
    body: Optional[str] = None,
    comments: Optional[List[Dict[str, Any]]] = None,
    serp_snippets: Optional[List[str]] = None,
    max_tokens: int = 8192
) -> str:
    """
    안전한 embedding_text 생성 (토큰 제한 준수)
    
    정책:
    - title: 전체 포함
    - body/selftext: 토큰 기준으로 max 1500~2000 (또는 문자 길이 기반 안전 제한)
    - comments: 상위 3~5개만, 각 200~300 토큰 제한
    - serp snippet: 1~2개만, 각 150~200 토큰 제한
    
    Args:
        title: 포스트 제목
        body: 포스트 본문 (선택)
        comments: 댓글 리스트 (각 dict는 'body', 'upvotes' 키 포함)
        serp_snippets: SERP 스니펫 리스트 (선택)
        max_tokens: 최대 토큰 수 (기본 8192)
    
    Returns:
        안전하게 구성된 embedding_text
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model("text-embedding-3-large")
        has_tiktoken = True
    except ImportError:
        has_tiktoken = False
        # 문자 길이 기반 추정 (1 토큰 ≈ 4 문자, 안전하게 3.5로 계산)
        chars_per_token = 3.5
    
    def count_tokens(text: str) -> int:
        """토큰 수 계산"""
        if has_tiktoken:
            return len(encoding.encode(text))
        else:
            return int(len(text) / chars_per_token)
    
    def truncate_to_tokens(text: str, max_tokens: int) -> str:
        """텍스트를 토큰 수 기준으로 자르기"""
        if not text:
            return ""
        if has_tiktoken:
            tokens = encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text
            truncated = encoding.decode(tokens[:max_tokens])
            return truncated
        else:
            max_chars = int(max_tokens * chars_per_token)
            if len(text) <= max_chars:
                return text
            return text[:max_chars]
    
    parts = []
    remaining_tokens = max_tokens
    
    # 1. Title: 전체 포함 (필수)
    clean_title = clean_text(title or "")
    if clean_title:
        title_tokens = count_tokens(clean_title)
        parts.append(clean_title)
        remaining_tokens -= title_tokens
    
    # 2. Body: 최대 2000 토큰 (우선순위 높음)
    if body and remaining_tokens > 500:
        clean_body = clean_text(body)
        if clean_body:
            body_max_tokens = min(2000, remaining_tokens - 1000)  # 댓글/스니펫 공간 확보
            if body_max_tokens > 0:
                truncated_body = truncate_to_tokens(clean_body, body_max_tokens)
                body_tokens = count_tokens(truncated_body)
                if truncated_body:
                    parts.append(f"\n\n{truncated_body}")
                    remaining_tokens -= body_tokens
    
    # 3. Comments: 상위 3~5개, 각 300 토큰 제한
    if comments and remaining_tokens > 500:
        # upvotes 기준 정렬
        sorted_comments = sorted(
            comments,
            key=lambda c: c.get('upvotes', 0),
            reverse=True
        )[:5]  # 최대 5개
        
        comment_texts = []
        for comment in sorted_comments[:5]:
            if remaining_tokens <= 300:
                break
            comment_body = clean_text(comment.get('body', ''))
            if comment_body:
                truncated_comment = truncate_to_tokens(comment_body, 300)
                comment_tokens = count_tokens(truncated_comment)
                if truncated_comment and comment_tokens <= remaining_tokens:
                    comment_texts.append(truncated_comment)
                    remaining_tokens -= comment_tokens
        
        if comment_texts:
            parts.append("\n\n--- Top Comments ---")
            for i, comment_text in enumerate(comment_texts, 1):
                parts.append(f"\n\nComment {i}: {comment_text}")
    
    # 4. SERP snippets: 1~2개, 각 200 토큰 제한
    if serp_snippets and remaining_tokens > 300:
        snippet_texts = []
        for snippet in serp_snippets[:2]:  # 최대 2개
            if remaining_tokens <= 200:
                break
            clean_snippet = clean_text(snippet)
            if clean_snippet:
                truncated_snippet = truncate_to_tokens(clean_snippet, 200)
                snippet_tokens = count_tokens(truncated_snippet)
                if truncated_snippet and snippet_tokens <= remaining_tokens:
                    snippet_texts.append(truncated_snippet)
                    remaining_tokens -= snippet_tokens
        
        if snippet_texts:
            parts.append("\n\n--- SERP Snippets ---")
            for i, snippet_text in enumerate(snippet_texts, 1):
                parts.append(f"\n\nSnippet {i}: {snippet_text}")
    
    result = "".join(parts)
    
    # 최종 검증: 토큰 수 확인
    final_tokens = count_tokens(result)
    if final_tokens > max_tokens:
        logger.warning(f"Embedding text exceeds max_tokens ({final_tokens} > {max_tokens}), truncating...")
        result = truncate_to_tokens(result, max_tokens)
    
    return result

def is_deleted_post(title: str, body: str) -> bool:
    """삭제된 글 체크"""
    deleted_patterns = [
        r'^\[deleted\]',
        r'^\[removed\]',
        r'^deleted',
        r'^removed'
    ]
    
    title_lower = (title or "").lower().strip()
    body_lower = (body or "").lower().strip()
    
    for pattern in deleted_patterns:
        if re.match(pattern, title_lower) or re.match(pattern, body_lower):
            return True
    
    return False

def get_text_hash(text: str) -> str:
    """Get SHA-256 hash of text (normalized)"""
    # 텍스트 정규화: 공백 정규화 후 해시
    normalized = re.sub(r'\s+', ' ', text.strip())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def preprocess_reddit_posts(run_id: int, dry_run: bool = False, 
                            min_length: int = MIN_TEXT_LENGTH,
                            max_docs: Optional[int] = None) -> Dict[str, Any]:
    """
    Preprocess Reddit posts: clean, filter, deduplicate
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode (no DB writes)
        min_length: Minimum text length (default: 30)
        max_docs: Maximum documents to process (for cost control, None = all)
    
    Returns:
        Statistics dictionary with preprocessed documents ready for embedding
    """
    conn = get_db_connection()
    stats = {
        "total_posts": 0,
        "title_empty": 0,
        "too_short": 0,
        "deleted": 0,
        "duplicates_removed": 0,
        "preprocessed": 0,
        "errors": []
    }
    
    # 중복 제거를 위한 hash -> (doc_id, score) 매핑
    # score = upvotes + num_comments (높은 것 우선)
    hash_to_best = {}  # {text_hash: (doc_id, score, meta)}
    
    try:
        with conn.cursor() as cur:
            # Get all raw posts (정렬: upvotes DESC, num_comments DESC)
            query = """
                SELECT reddit_post_id, title, body, created_utc, 
                       upvotes, num_comments, permalink, keyword
                FROM raw_reddit_posts
                ORDER BY upvotes DESC, num_comments DESC
            """
            
            if max_docs:
                query += f" LIMIT {max_docs}"
            
            cur.execute(query)
            all_posts = cur.fetchall()
            stats["total_posts"] = len(all_posts)
            
            logger.info(f"Preprocessing {stats['total_posts']} Reddit posts (max_docs={max_docs or 'all'})")
            
            for post_id, title, body, created_utc, upvotes, num_comments, permalink, keyword in all_posts:
                try:
                    # 1. title이 비어있으면 제거
                    if not title or not title.strip():
                        stats["title_empty"] += 1
                        continue
                    
                    # 2. 삭제된 글 체크
                    if is_deleted_post(title, body):
                        stats["deleted"] += 1
                        continue
                    
                    # 3. 분석용 텍스트 생성
                    analysis_text = build_analysis_text(title, body)
                    
                    # 4. 너무 짧은 글 제거
                    if len(analysis_text) < min_length:
                        stats["too_short"] += 1
                        continue
                    
                    # 5. text_hash 생성
                    text_hash = get_text_hash(analysis_text)
                    
                    # 6. 중복 제거: score = upvotes + num_comments
                    score = (upvotes or 0) + (num_comments or 0)
                    
                    if text_hash in hash_to_best:
                        # 기존 것과 비교하여 score가 높은 것 선택
                        existing_score = hash_to_best[text_hash][1]
                        if score > existing_score:
                            hash_to_best[text_hash] = (
                                post_id,
                                score,
                                {
                                    "text": analysis_text,
                                    "text_hash": text_hash,
                                    "upvotes": upvotes or 0,
                                    "num_comments": num_comments or 0,
                                    "created_utc": created_utc,
                                    "keyword": keyword,
                                    "permalink": permalink
                                }
                            )
                            stats["duplicates_removed"] += 1
                        else:
                            stats["duplicates_removed"] += 1
                    else:
                        # 새로운 hash
                        hash_to_best[text_hash] = (
                            post_id,
                            score,
                            {
                                "text": analysis_text,
                                "text_hash": text_hash,
                                "upvotes": upvotes or 0,
                                "num_comments": num_comments or 0,
                                "created_utc": created_utc,
                                "keyword": keyword,
                                "permalink": permalink
                            }
                        )
                
                except Exception as e:
                    logger.error(f"Error preprocessing post {post_id}: {e}")
                    stats["errors"].append(str(e))
            
            # 최종 전처리된 문서들
            preprocessed_docs = []
            for text_hash, (doc_id, score, meta) in hash_to_best.items():
                preprocessed_docs.append({
                    "doc_type": "reddit_post",
                    "doc_id": doc_id,
                    "text": meta["text"],
                    "text_hash": text_hash,
                    "meta": {
                        "upvotes": meta["upvotes"],
                        "num_comments": meta["num_comments"],
                        "created_utc": meta["created_utc"],
                        "keyword": meta["keyword"],
                        "permalink": meta["permalink"]
                    }
                })
            
            stats["preprocessed"] = len(preprocessed_docs)
            
            if dry_run:
                logger.info(f"[DRY RUN] Preprocessing results:")
                logger.info(f"  Total posts: {stats['total_posts']}")
                logger.info(f"  Title empty: {stats['title_empty']}")
                logger.info(f"  Too short: {stats['too_short']}")
                logger.info(f"  Deleted: {stats['deleted']}")
                logger.info(f"  Duplicates removed: {stats['duplicates_removed']}")
                logger.info(f"  Preprocessed: {stats['preprocessed']}")
                
                # 샘플 출력
                for i, doc in enumerate(preprocessed_docs[:5], 1):
                    logger.info(f"  Sample {i}: {doc['doc_id']} - {doc['text'][:60]}...")
            else:
                # 실제로는 embedding 단계에서 처리되므로 여기서는 통계만 반환
                logger.info(f"Preprocessing completed:")
                logger.info(f"  Total posts: {stats['total_posts']}")
                logger.info(f"  Title empty: {stats['title_empty']}")
                logger.info(f"  Too short: {stats['too_short']}")
                logger.info(f"  Deleted: {stats['deleted']}")
                logger.info(f"  Duplicates removed: {stats['duplicates_removed']}")
                logger.info(f"  Preprocessed: {stats['preprocessed']}")
    
    finally:
        conn.close()
    
    # embedding 단계에서 사용할 수 있도록 preprocessed_docs도 반환
    stats["preprocessed_docs"] = preprocessed_docs if not dry_run else []
    
    return stats
