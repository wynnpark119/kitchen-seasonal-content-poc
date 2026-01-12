"""
Reddit 데이터 프루닝(제거) 모듈

포스트 및 키워드 단위 필터링 규칙 적용
"""
import re
from typing import List, Dict, Any, Tuple
from .db import get_db_connection
from .logging import setup_logger

logger = setup_logger("pruning")

# Negative keywords (정규식 패턴)
NEGATIVE_PATTERNS = {
    "purchase": re.compile(r'\b(buy|purchase|price|cost|affordable|cheap|expensive|worth it|recommend|review|comparison|vs|which one|better|best brand|where to buy|deal|sale|discount)\b', re.IGNORECASE),
    "repair": re.compile(r'\b(not cooling|broken|repair|error code|warranty|compressor|ice maker|defrost|leaking|not working|stopped|faulty|malfunction|service|technician|fix|damaged)\b', re.IGNORECASE),
    "noise": re.compile(r'\b(spring break|spring mattress|coil spring|engine spring|spring water|hair styling|fashion styling|nail styling|makeup styling|vegetable gardening|vegetable planting|vegetable seeds|vegetable growing)\b', re.IGNORECASE),
    "brand": re.compile(r'\b(model|spec|specification|Samsung|LG|Whirlpool|KitchenAid|GE|Bosch|Maytag|Frigidaire)\b', re.IGNORECASE)
}

def check_immediate_kill(post_title: str, post_body: str) -> Tuple[bool, str]:
    """
    포스트 즉시 제거 조건 체크
    
    Returns:
        (should_kill, reason)
    """
    text = f"{post_title} {post_body}".lower()
    
    # 구매/추천/비교
    if NEGATIVE_PATTERNS["purchase"].search(text):
        return True, "purchase/recommendation"
    
    # 고장/수리/AS
    if NEGATIVE_PATTERNS["repair"].search(text):
        return True, "repair/AS"
    
    # 노이즈 오탐
    if NEGATIVE_PATTERNS["noise"].search(text):
        return True, "noise/off-topic"
    
    # 브랜드/모델 중심
    if NEGATIVE_PATTERNS["brand"].search(text):
        return True, "brand/model focused"
    
    return False, ""

def check_conditional_remove(post_title: str, post_body: str, num_comments: int) -> Tuple[bool, str]:
    """
    조건부 제거 조건 체크
    
    Returns:
        (should_remove, reason)
    """
    # 정보 밀도 낮음
    if len(post_body.strip()) < 50:
        return True, "low information density"
    
    # 댓글 거의 없음 + 질문 막연함
    if num_comments <= 1 and len(post_body.strip()) < 100:
        vague_patterns = ["any tips", "any ideas", "help", "advice"]
        if any(pattern in post_body.lower() for pattern in vague_patterns):
            return True, "vague question with few comments"
    
    return False, ""

def check_keep(post_title: str, post_body: str, num_comments: int, top_comment_upvotes: int = 0) -> bool:
    """
    유지 조건 체크
    """
    # 댓글에 경험 공유/토론 존재
    if num_comments >= 3 or top_comment_upvotes >= 10:
        return True
    
    # 실제 생활자 고민이 명확
    how_to_patterns = ["how do you", "how to", "what do you", "best way to", "tips for"]
    if any(pattern in post_title.lower() or pattern in post_body.lower() for pattern in how_to_patterns):
        if len(post_body.strip()) >= 100:  # 구체적 설명 있음
            return True
    
    return False

def evaluate_post(post: Dict[str, Any]) -> Tuple[str, str]:
    """
    포스트 단위 판정
    
    Returns:
        (verdict, reason)
        verdict: "KEEP", "DROP", "REVIEW"
    """
    title = post.get('title', '')
    body = post.get('selftext', '') or post.get('body', '')
    num_comments = post.get('num_comments', 0)
    top_comment_upvotes = post.get('top_comment_upvotes', 0)
    
    # 즉시 제거 체크
    should_kill, kill_reason = check_immediate_kill(title, body)
    if should_kill:
        return "DROP", kill_reason
    
    # 조건부 제거 체크
    should_remove, remove_reason = check_conditional_remove(title, body, num_comments)
    if should_remove:
        return "DROP", remove_reason
    
    # 유지 조건 체크
    if check_keep(title, body, num_comments, top_comment_upvotes):
        return "KEEP", "meets keep criteria"
    
    # 애매한 경우
    return "REVIEW", "unclear"

def evaluate_keyword(keyword: str, sample_posts: List[Dict[str, Any]]) -> Tuple[str, str, Dict[str, int]]:
    """
    키워드 단위 판정
    
    Args:
        keyword: 키워드
        sample_posts: 샘플 포스트 리스트 (최대 10개)
    
    Returns:
        (verdict, reason, stats)
        verdict: "KEEP", "DROP", "REVIEW"
        stats: 판정 통계
    """
    if not sample_posts:
        return "DROP", "no posts found", {}
    
    # 각 포스트 판정
    verdicts = []
    drop_reasons = []
    
    for post in sample_posts:
        verdict, reason = evaluate_post(post)
        verdicts.append(verdict)
        if verdict == "DROP":
            drop_reasons.append(reason)
    
    stats = {
        "total": len(verdicts),
        "keep": verdicts.count("KEEP"),
        "drop": verdicts.count("DROP"),
        "review": verdicts.count("REVIEW")
    }
    
    drop_ratio = stats["drop"] / stats["total"] if stats["total"] > 0 else 0
    
    # 키워드 삭제 후보 조건 체크
    candidate_flags = []
    
    # 1. 오탐/제외 대상 50% 이상
    if drop_ratio >= 0.5:
        candidate_flags.append("high_drop_ratio")
    
    # 2. 구매/고장/AS 주류 (간단 체크)
    purchase_repair_count = sum(1 for reason in drop_reasons if reason in ["purchase/recommendation", "repair/AS"])
    if purchase_repair_count >= len(sample_posts) * 0.5:
        candidate_flags.append("purchase_repair_dominant")
    
    # 키워드 삭제 확정: 후보 조건 2개 이상
    if len(candidate_flags) >= 2:
        return "DROP", f"keyword_kill: {', '.join(candidate_flags)}", stats
    
    # 대부분 KEEP이면 KEEP
    if stats["keep"] >= stats["total"] * 0.7:
        return "KEEP", "mostly valid posts", stats
    
    # 애매한 경우
    return "REVIEW", "mixed results", stats

def get_keyword_samples(keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
    """키워드별 샘플 포스트 추출"""
    conn = get_db_connection()
    posts = []
    
    try:
        with conn.cursor() as cur:
            # 상위 포스트 추출
            cur.execute("""
                SELECT 
                    rp.reddit_post_id,
                    rp.title,
                    rp.body,
                    rp.subreddit,
                    rp.upvotes,
                    rp.num_comments,
                    rp.permalink,
                    rp.author,
                    rp.keyword
                FROM raw_reddit_posts rp
                WHERE rp.keyword = %s
                ORDER BY rp.upvotes DESC, rp.num_comments DESC
                LIMIT %s
            """, (keyword, limit))
            
            for row in cur.fetchall():
                post_id = row[0]
                
                # Top 1-2 댓글 가져오기
                cur.execute("""
                    SELECT upvotes
                    FROM raw_reddit_comments
                    WHERE reddit_post_id = %s
                    ORDER BY upvotes DESC
                    LIMIT 1
                """, (post_id,))
                
                top_comment = cur.fetchone()
                top_comment_upvotes = top_comment[0] if top_comment else 0
                
                posts.append({
                    'reddit_post_id': post_id,
                    'title': row[1],
                    'body': row[2],
                    'selftext': row[2],  # Alias for compatibility
                    'subreddit': row[3],
                    'upvotes': row[4],
                    'num_comments': row[5],
                    'permalink': row[6],
                    'author': row[7],
                    'keyword': row[8],
                    'top_comment_upvotes': top_comment_upvotes
                })
    
    finally:
        conn.close()
    
    return posts

def prune_keywords() -> Dict[str, Any]:
    """
    모든 키워드에 대해 프루닝 수행
    
    Returns:
        {
            "keep": [...],
            "drop": [...],
            "review": [...],
            "stats": {...}
        }
    """
    from .config import REDDIT_KEYWORDS
    
    # 모든 키워드 수집
    all_keywords = []
    for category, keywords in REDDIT_KEYWORDS.items():
        all_keywords.extend(keywords)
    
    results = {
        "keep": [],
        "drop": [],
        "review": [],
        "stats": {
            "total_keywords": len(all_keywords),
            "total_posts_evaluated": 0
        }
    }
    
    logger.info(f"Evaluating {len(all_keywords)} keywords")
    
    for keyword in all_keywords:
        # 샘플 추출
        samples = get_keyword_samples(keyword, limit=10)
        
        if not samples:
            results["drop"].append({
                "keyword": keyword,
                "reason": "no posts found",
                "stats": {}
            })
            continue
        
        # 키워드 판정
        verdict, reason, stats = evaluate_keyword(keyword, samples)
        
        keyword_result = {
            "keyword": keyword,
            "verdict": verdict,
            "reason": reason,
            "stats": stats,
            "sample_count": len(samples)
        }
        
        results[verdict.lower()].append(keyword_result)
        results["stats"]["total_posts_evaluated"] += len(samples)
        
        logger.info(f"{keyword}: {verdict} - {reason}")
    
    # 최종 통계
    results["stats"]["keep_count"] = len(results["keep"])
    results["stats"]["drop_count"] = len(results["drop"])
    results["stats"]["review_count"] = len(results["review"])
    
    return results
