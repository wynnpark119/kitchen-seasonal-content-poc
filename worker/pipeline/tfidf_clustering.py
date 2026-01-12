"""
TF-IDF 기반 4개 클러스터링 (임베딩 없이)

subreddit 기반으로 Reddit 포스트를 4개 카테고리로 분류
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
import json
from psycopg2.extras import Json as PsycopgJson

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import numpy as np

from .db import get_db_connection, put_db_connection, upsert_cluster_assignment
from .config import CATEGORIES
from .preprocess import clean_text, is_deleted_post
from .logging import setup_logger

logger = setup_logger("tfidf_clustering")

# 카테고리별 허용 subreddit 목록 (주요 필터)
CATEGORY_SUBREDDITS = {
    "SPRING_RECIPES": [
        "cooking", "recipes", "food", "baking", "mealprep", "cookingforbeginners",
        "askculinary", "whatshouldicook", "tonightsdinner", "foodporn", "cookingvideos",
        "slowcooking", "instantpot", "sousvide", "grilling", "bbq", "vegetarian",
        "veganrecipes", "ketorecipes", "mealprepsunday", "eatcheapandhealthy"
    ],
    "SPRING_KITCHEN_STYLING": [
        "interiordesign", "homeimprovement", "diy", "decor", "homedecorating",
        "roomporn", "amateurroomporn", "cozyplaces", "malelivingspace",
        "femalelivingspace", "designmyroom", "kitchenporn"
    ],
    "REFRIGERATOR_ORGANIZATION": [
        "organization", "declutter", "konmari", "organizationporn", "mealprep",
        "fridge", "kitchenorganization", "homeorganization", "organization"
    ],
    "VEGETABLE_PREP_HANDLING": [
        "mealprep", "cooking", "recipes", "food", "vegetarian", "veganrecipes",
        "eatcheapandhealthy", "cookingforbeginners", "whatshouldicook"
    ]
}

# 카테고리별 키워드 (보조 신호로만 사용, stopword 제외)
CATEGORY_KEYWORDS = {
    "SPRING_RECIPES": [
        "recipe", "dinner", "meal", "cook", "food", "dish", 
        "ingredient", "cooking", "prep", "meal prep", "bake", "roast", "grill"
    ],
    "SPRING_KITCHEN_STYLING": [
        "decor", "decoration", "styling", "design", "kitchen",
        "refresh", "makeover", "update", "color", "accessory", "centerpiece", "renovation"
    ],
    "REFRIGERATOR_ORGANIZATION": [
        "refrigerator", "fridge", "organization", "organize", "storage",
        "container", "bin", "label", "shelf", "drawer", "door", "organize"
    ],
    "VEGETABLE_PREP_HANDLING": [
        "vegetable", "prep", "preparation", "storage", "wash", "clean",
        "cut", "chop", "store", "container", "fresh", "preserve", "vegetables"
    ]
}

# 제외할 subreddit (명시적으로 제외)
EXCLUDED_SUBREDDITS = [
    "aita", "amitheasshole", "relationship_advice", "relationships", "tifu",
    "unpopularopinion", "changemyview", "offmychest", "confession", "advice",
    "legaladvice", "personalfinance", "explainlikeimfive", "askreddit", "funny",
    "mildlyinteresting", "pics", "gifs", "videos", "gaming", "movies", "television"
]


def extract_text_from_post(title: str, body: Optional[str]) -> str:
    """포스트에서 분석용 텍스트 추출"""
    clean_title = clean_text(title or "")
    clean_body = clean_text(body or "")
    
    if clean_body:
        return f"{clean_title} {clean_body}"
    return clean_title


def assign_post_to_category(post_text: str, keyword: Optional[str] = None, 
                            subreddit: Optional[str] = None) -> Optional[str]:
    """
    포스트를 카테고리로 할당 (subreddit 기반 + 키워드 보조)
    
    Args:
        post_text: 포스트 텍스트 (title + body)
        keyword: 포스트의 keyword 필드 (선택적)
        subreddit: 포스트의 subreddit (필수)
    
    Returns:
        카테고리명 (CATEGORIES 중 하나) 또는 None (매칭 실패 시)
    """
    # subreddit이 없으면 None 반환 (분류 불가)
    if not subreddit:
        return None
    
    subreddit_lower = subreddit.lower()
    
    # 1. 제외할 subreddit 체크
    if subreddit_lower in [s.lower() for s in EXCLUDED_SUBREDDITS]:
        return None
    
    # 2. subreddit 기반 매칭 (주요 필터)
    matched_categories = []
    for category, allowed_subreddits in CATEGORY_SUBREDDITS.items():
        for allowed_sub in allowed_subreddits:
            if allowed_sub.lower() in subreddit_lower:
                matched_categories.append(category)
                break
    
    # subreddit 매칭이 있으면 그 중에서 키워드로 선별
    if matched_categories:
        post_lower = post_text.lower()
        
        # keyword 필드가 있으면 우선 사용
        if keyword:
            keyword_lower = keyword.lower()
            for category in matched_categories:
                for kw in CATEGORY_KEYWORDS[category]:
                    if kw in keyword_lower:
                        return category
        
        # 텍스트 기반 매칭 (보조 신호)
        category_scores = {}
        for category in matched_categories:
            score = 0
            for kw in CATEGORY_KEYWORDS[category]:
                # 단어 경계를 고려한 매칭 (stopword 방지)
                import re
                pattern = r'\b' + re.escape(kw) + r'\b'
                matches = len(re.findall(pattern, post_lower))
                score += matches
            category_scores[category] = score
        
        # 가장 높은 점수의 카테고리 반환
        if max(category_scores.values()) > 0:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        # 키워드 매칭 실패 시 첫 번째 매칭된 카테고리 반환
        return matched_categories[0]
    
    # 3. subreddit 매칭 실패 시 None 반환 (기본값 할당 금지)
    return None


def extract_top_keywords(texts: List[str], top_n: int = 20) -> List[Tuple[str, float]]:
    """
    TF-IDF 기반 상위 키워드 추출
    
    Args:
        texts: 텍스트 리스트
        top_n: 상위 N개 키워드
    
    Returns:
        [(keyword, tfidf_score), ...] 리스트
    """
    if not texts:
        return []
    
    try:
        # 확장된 stop words 리스트
        extended_stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'up', 'about', 'into', 'through', 'during', 'including', 'against', 'among',
            'throughout', 'despite', 'towards', 'upon', 'concerning', 'to', 'of', 'in', 'for',
            'on', 'at', 'by', 'with', 'from', 'up', 'about', 'into', 'through', 'during',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
            'do', 'does', 'did', 'doing', 'will', 'would', 'shall', 'should', 'may', 'might',
            'must', 'can', 'could', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when',
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 'just', 'like', 'time', 'times', 've', 'don', 'doesn', 'didn', 'isn',
            'aren', 'wasn', 'weren', 'hasn', 'haven', 'hadn', 'won', 'wouldn', 'shan',
            'shouldn', 'mightn', 'mustn', 'can', 'couldn', 'https', 'http', 'www', 'com'
        }
        
        vectorizer = TfidfVectorizer(
            max_features=top_n * 3,  # 여유있게 추출 후 상위 N개 선택
            stop_words=list(extended_stop_words),
            ngram_range=(1, 2),  # 단어 및 2-gram
            min_df=2,  # 최소 2개 문서에서 나타나야 함
            max_df=0.9  # 최대 90% 문서에서 나타날 수 있음
        )
        
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        # 평균 TF-IDF 점수 계산
        mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
        
        # 상위 N개 선택
        top_indices = np.argsort(mean_scores)[-top_n:][::-1]
        
        return [(feature_names[i], float(mean_scores[i])) for i in top_indices]
    except Exception as e:
        logger.warning(f"TF-IDF 키워드 추출 실패: {e}, 빈도 기반으로 대체")
        # Fallback: 단순 빈도 기반
        word_counts = Counter()
        for text in texts:
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            word_counts.update(words)
        
        # Stop words 제거
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'way', 'use', 'her', 'she', 'many', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'much', 'over', 'such', 'take', 'than', 'them', 'well', 'were'}
        filtered_counts = Counter({k: v for k, v in word_counts.items() if k not in stop_words})
        
        return [(word, float(count)) for word, count in filtered_counts.most_common(top_n)]


def determine_optimal_k(n_samples: int, min_k: int = 2, max_k: int = 10, target_k: int = 4) -> int:
    """
    데이터 분포에 따라 최적의 클러스터 개수 결정
    
    Args:
        n_samples: 샘플 수
        min_k: 최소 클러스터 개수
        max_k: 최대 클러스터 개수
        target_k: 목표 클러스터 개수 (각 주제별 4개)
    
    Returns:
        최적의 클러스터 개수
    """
    # 각 주제별 4개를 목표로 하되, 데이터가 충분하지 않으면 조정
    if n_samples < min_k:
        return 1
    elif n_samples < 20:
        return min(2, n_samples // 5)
    elif n_samples < 50:
        return min(3, n_samples // 10)
    elif n_samples < 100:
        return min(target_k, n_samples // 15)
    else:
        # 데이터가 충분하면 목표 개수 사용 (각 주제별 4개)
        return min(max_k, max(min_k, target_k))


def cluster_posts_within_category(
    posts: List[Dict[str, Any]],
    category: str
) -> List[Dict[int, List[Dict[str, Any]]]]:
    """
    특정 카테고리 내에서 포스트들을 여러 sub-cluster로 분류
    
    Args:
        posts: 카테고리 내 포스트 리스트
        category: 카테고리명
    
    Returns:
        클러스터 그룹 딕셔너리 리스트 (각 딕셔너리는 cluster_label -> posts)
    """
    if len(posts) == 0:
        return []
    
    if len(posts) < 5:
        # 포스트가 너무 적으면 1개 클러스터로 처리
        return [{-1: posts}]  # -1은 단일 클러스터를 의미
    
    # TF-IDF 벡터화
    texts = [p['text'] for p in posts]
    
    try:
        vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # 최적의 K 결정 (각 주제별 4개 목표)
        optimal_k = determine_optimal_k(len(posts), target_k=4)
        
        if optimal_k == 1:
            # 클러스터링 불필요, 단일 클러스터
            return [{-1: posts}]
        
        # K-means 클러스터링
        kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(tfidf_matrix.toarray())
        
        # 클러스터별로 그룹화
        cluster_groups = {}
        for idx, label in enumerate(cluster_labels):
            if label not in cluster_groups:
                cluster_groups[label] = []
            cluster_groups[label].append(posts[idx])
        
        # 딕셔너리 리스트로 변환
        return [{label: cluster_posts} for label, cluster_posts in cluster_groups.items()]
    
    except Exception as e:
        logger.warning(f"클러스터링 실패 ({category}): {e}, 단일 클러스터로 처리")
        return [{-1: posts}]


def generate_cluster_summary(
    posts: List[Dict[str, Any]],
    top_keywords: List[Tuple[str, float]]
) -> str:
    """
    클러스터 요약 텍스트 생성 (3~5줄)
    
    Args:
        posts: 클러스터 내 포스트 리스트
        top_keywords: 상위 키워드 리스트
    
    Returns:
        요약 텍스트
    """
    if not posts:
        return ""
    
    # 대표 포스트 제목들
    top_titles = [p['title'] for p in posts[:5] if p.get('title')]
    
    # 키워드 문자열
    keywords_str = ", ".join([kw for kw, _ in top_keywords[:10]])
    
    # 요약 생성
    summary_parts = []
    
    # 첫 줄: 주제 소개
    if top_keywords:
        main_topic = top_keywords[0][0]
        summary_parts.append(f"This cluster focuses on {main_topic} and related topics.")
    
    # 두 번째 줄: 주요 키워드
    if keywords_str:
        summary_parts.append(f"Key themes include: {keywords_str}.")
    
    # 세 번째 줄: 포스트 특성
    if top_titles:
        summary_parts.append(f"Discussions cover topics like: {', '.join(top_titles[:3])}.")
    
    # 네 번째 줄: 참여도
    total_upvotes = sum(p.get('upvotes', 0) for p in posts)
    total_comments = sum(p.get('num_comments', 0) for p in posts)
    if total_upvotes > 0 or total_comments > 0:
        summary_parts.append(f"Community engagement: {total_upvotes} upvotes and {total_comments} comments across {len(posts)} posts.")
    
    return " ".join(summary_parts[:5])  # 최대 5줄


def run_tfidf_clustering(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    TF-IDF 기반 클러스터링 실행 (각 topic_category별로 독립적으로 수행)
    
    각 topic_category는 독립적인 입력 그룹이며, 각각에 대해 별도로 클러스터링을 수행합니다.
    각 카테고리 내에서 여러 sub-cluster를 생성합니다.
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
    
    Returns:
        Statistics dictionary (topic_category별로 분리된 통계 포함)
    """
    logger.info("Starting TF-IDF based clustering (per topic_category)")
    logger.info("각 topic_category별로 독립적으로 클러스터링 수행")
    
    stats = {
        "posts_processed": 0,
        "clusters_created": 0,
        "assignments_created": 0,
        "categories": {}  # topic_category별 통계
    }
    
    # 1. Reddit 포스트 로드
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT reddit_post_id, title, body, upvotes, num_comments, keyword, subreddit
                FROM raw_reddit_posts
                WHERE title IS NOT NULL
                AND LENGTH(COALESCE(title, '')) > 0
                ORDER BY upvotes DESC, num_comments DESC
            """)
            
            all_posts = cur.fetchall()
            stats["posts_processed"] = len(all_posts)
            
            logger.info(f"Loaded {len(all_posts)} Reddit posts")
    finally:
        if conn:
            put_db_connection(conn)
    
    if stats["posts_processed"] == 0:
        logger.warning("No posts found, skipping clustering")
        return stats
    
    # 2. 카테고리별로 포스트 분류
    category_posts = {category: [] for category in CATEGORIES}
    
    for post_id, title, body, upvotes, num_comments, keyword, subreddit in all_posts:
        # 삭제된 글 스킵
        if is_deleted_post(title, body):
            continue
        
        # 텍스트 추출
        post_text = extract_text_from_post(title, body)
        
        # 카테고리 할당 (subreddit 포함)
        category = assign_post_to_category(post_text, keyword, subreddit)
        
        # 카테고리 할당 실패 시 스킵 (기본값 할당 금지)
        if category is None:
            continue
        
        category_posts[category].append({
            "post_id": post_id,
            "title": title,
            "body": body,
            "upvotes": upvotes or 0,
            "num_comments": num_comments or 0,
            "text": post_text,
            "subreddit": subreddit
        })
    
    logger.info("=" * 80)
    logger.info("Posts assigned to categories:")
    for category, posts in category_posts.items():
        logger.info(f"  {category}: {len(posts)} posts")
    logger.info("=" * 80)
    
    # 3. 각 카테고리별로 독립적으로 클러스터링 수행
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for category in CATEGORIES:
                posts = category_posts[category]
                
                # 카테고리별 통계 초기화
                category_stats = {
                    "post_count": len(posts),
                    "sub_clusters_created": 0,
                    "status": "processed" if len(posts) > 0 else "no_data"
                }
                
                if len(posts) == 0:
                    logger.warning(f"⚠️  {category}: 데이터 없음 (post 수: 0)")
                    category_stats["status"] = "no_data"
                    stats["categories"][category] = category_stats
                    continue
                
                logger.info("")
                logger.info("=" * 80)
                logger.info(f"📌 {category} 클러스터링 시작 (포스트 수: {len(posts)})")
                logger.info("=" * 80)
                
                # 각 카테고리 내에서 여러 sub-cluster 생성
                cluster_groups = cluster_posts_within_category(posts, category)
                
                logger.info(f"생성된 sub-cluster 수: {len(cluster_groups)}")
                
                # 각 sub-cluster에 대해 처리
                for cluster_idx, cluster_group in enumerate(cluster_groups):
                    cluster_label, cluster_posts = list(cluster_group.items())[0]
                    
                    if len(cluster_posts) == 0:
                        continue
                    
                    # 대표 포스트 선택 (upvotes + num_comments 기준)
                    posts_sorted = sorted(
                        cluster_posts,
                        key=lambda p: p['upvotes'] + p['num_comments'],
                        reverse=True
                    )
                    representative_posts = posts_sorted[:min(10, len(posts_sorted))]
                    
                    # 상위 키워드 추출
                    texts = [p['text'] for p in cluster_posts]
                    top_keywords = extract_top_keywords(texts, top_n=20)
                    
                    # 클러스터 요약 생성
                    summary = generate_cluster_summary(cluster_posts, top_keywords)
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would create sub-cluster {cluster_idx + 1} ({category}):")
                        logger.info(f"  Posts: {len(cluster_posts)}")
                        logger.info(f"  Representative posts: {len(representative_posts)}")
                        logger.info(f"  Top keywords: {[kw for kw, _ in top_keywords[:5]]}")
                        logger.info(f"  Summary: {summary[:100]}...")
                        category_stats["sub_clusters_created"] += 1
                        continue
                    
                    # 클러스터 저장
                    params = {
                        "method": "tfidf_kmeans",
                        "topic_category": category,
                        "sub_cluster_index": cluster_idx,
                        "top_keywords": [kw for kw, _ in top_keywords],
                        "representative_post_ids": [p['post_id'] for p in representative_posts],
                        "summary": summary
                    }
                    
                    cur.execute("""
                        INSERT INTO clusters (
                            algorithm, params_json, noise_label, size, created_from_run_id
                        ) VALUES (%s, %s, %s, %s, %s)
                        RETURNING cluster_id
                    """, (
                        "TF-IDF_KMEANS",
                        PsycopgJson(params),
                        False,
                        len(cluster_posts),
                        run_id
                    ))
                    
                    cluster_id = cur.fetchone()[0]
                    stats["clusters_created"] += 1
                    category_stats["sub_clusters_created"] += 1
                    
                    # 클러스터 INSERT를 먼저 commit (foreign key 제약 조건을 위해)
                    conn.commit()
                    
                    # 클러스터 할당 저장
                    for post in cluster_posts:
                        upsert_cluster_assignment(
                            cluster_id=cluster_id,
                            doc_type="reddit_post",
                            doc_id=post['post_id'],
                            distance=0.0,  # TF-IDF 기반이므로 거리 개념 없음
                            is_representative=post['post_id'] in [p['post_id'] for p in representative_posts],
                            run_id=run_id
                        )
                        stats["assignments_created"] += 1
                    
                    logger.info(f"  ✅ Sub-cluster {cluster_idx + 1} (cluster_id={cluster_id}): {len(cluster_posts)} posts")
                    logger.info(f"     대표 키워드: {', '.join([kw for kw, _ in top_keywords[:5]])}")
                    if representative_posts:
                        logger.info(f"     대표 포스트: {representative_posts[0]['title'][:60]}...")
                    
                    # 할당 저장 완료 후 commit (이미 clusters는 위에서 commit됨)
                    # upsert_cluster_assignment가 자체적으로 commit하므로 여기서는 불필요하지만
                    # 일관성을 위해 유지
                
                stats["categories"][category] = category_stats
                logger.info(f"✅ {category} 완료: {category_stats['sub_clusters_created']}개 sub-cluster 생성")
    
    finally:
        if conn:
            put_db_connection(conn)
    
    # 최종 통계 출력
    logger.info("")
    logger.info("=" * 80)
    logger.info("클러스터링 완료 - topic_category별 결과")
    logger.info("=" * 80)
    logger.info(f"전체 처리된 포스트 수: {stats['posts_processed']}")
    logger.info(f"전체 생성된 클러스터 수: {stats['clusters_created']}")
    logger.info(f"전체 할당 수: {stats['assignments_created']}")
    logger.info("")
    logger.info("topic_category별 상세 결과:")
    for category, cat_stats in stats["categories"].items():
        if cat_stats["status"] == "no_data":
            logger.info(f"  {category}: 데이터 없음 (post 수: 0)")
        else:
            logger.info(f"  {category}:")
            logger.info(f"    - 포스트 수: {cat_stats['post_count']}")
            logger.info(f"    - 생성된 sub-cluster 수: {cat_stats['sub_clusters_created']}")
    logger.info("=" * 80)
    
    return stats
