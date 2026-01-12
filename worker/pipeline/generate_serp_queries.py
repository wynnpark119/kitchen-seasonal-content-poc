"""
클러스터별 SERP 질문 생성 (각 클러스터당 50개)

정보 탐색/문제 인식/비교/사례/트렌드 중심의 검색 질문 생성
"""
import re
from typing import List, Dict, Any, Optional
from .db import get_db_connection, put_db_connection
from .logging import setup_logger

logger = setup_logger("generate_serp_queries")

# 질문 템플릿 (카테고리별)
QUERY_TEMPLATES = {
    "info_search": [
        "why do people {verb} {topic}",
        "how to {verb} {topic}",
        "what is the best way to {verb} {topic}",
        "how do you {verb} {topic}",
        "what are the benefits of {topic}",
        "why is {topic} important",
        "how does {topic} work",
        "what makes {topic} effective",
        "how to improve {topic}",
        "what are the steps to {verb} {topic}"
    ],
    "problem": [
        "common problems with {topic}",
        "{topic} challenges",
        "why do people struggle with {topic}",
        "difficulties with {topic}",
        "{topic} issues",
        "problems when {verb} {topic}",
        "mistakes when {verb} {topic}",
        "what goes wrong with {topic}",
        "{topic} pain points",
        "why {topic} fails"
    ],
    "comparison": [
        "{topic} vs {alternative} pros cons",
        "best {topic} for {use_case}",
        "{topic} vs {alternative} comparison",
        "which {topic} is better",
        "{topic} alternatives",
        "difference between {topic} and {alternative}",
        "{topic} options comparison",
        "choosing the right {topic}",
        "{topic} vs {alternative} which one",
        "best {topic} brands"
    ],
    "case_study": [
        "real world examples of {topic}",
        "{topic} success stories",
        "{topic} case studies",
        "how people use {topic}",
        "{topic} in practice",
        "examples of {topic}",
        "{topic} real life applications",
        "{topic} user experiences",
        "{topic} testimonials",
        "{topic} before and after"
    ],
    "trend": [
        "{topic} trends 2025",
        "future of {topic}",
        "{topic} innovations",
        "latest {topic} trends",
        "{topic} new developments",
        "emerging {topic}",
        "{topic} market trends",
        "{topic} industry trends",
        "{topic} upcoming changes",
        "{topic} predictions 2025"
    ]
}


def extract_topic_from_cluster(cluster_info: Dict[str, Any]) -> str:
    """
    클러스터 정보에서 주제 추출
    
    Args:
        cluster_info: 클러스터 정보 (top_keywords, category 등 포함)
    
    Returns:
        주제 키워드
    """
    # 상위 키워드에서 주제 추출
    if cluster_info.get("top_keywords"):
        top_kw = cluster_info["top_keywords"][0]
        if isinstance(top_kw, dict):
            return top_kw.get("keyword", "")
        elif isinstance(top_kw, tuple):
            return top_kw[0]
        else:
            return str(top_kw)
    
    # 카테고리 기반 주제
    category = cluster_info.get("category", "")
    category_topics = {
        "SPRING_RECIPES": "spring recipes",
        "SPRING_KITCHEN_STYLING": "spring kitchen decor",
        "REFRIGERATOR_ORGANIZATION": "refrigerator organization",
        "VEGETABLE_PREP_HANDLING": "vegetable prep"
    }
    
    return category_topics.get(category, "kitchen organization")


def extract_verbs_from_cluster(cluster_info: Dict[str, Any]) -> List[str]:
    """클러스터에서 동사 추출"""
    verbs = {
        "SPRING_RECIPES": ["cook", "prepare", "make", "create"],
        "SPRING_KITCHEN_STYLING": ["decorate", "style", "design", "refresh"],
        "REFRIGERATOR_ORGANIZATION": ["organize", "arrange", "store", "manage"],
        "VEGETABLE_PREP_HANDLING": ["prep", "prepare", "store", "wash", "clean"]
    }
    
    category = cluster_info.get("category", "")
    return verbs.get(category, ["organize", "manage", "use"])


def generate_queries_for_cluster(
    cluster_id: int,
    cluster_info: Dict[str, Any],
    num_queries: int = 50
) -> List[Dict[str, str]]:
    """
    클러스터별 검색 질문 생성
    
    Args:
        cluster_id: 클러스터 ID
        cluster_info: 클러스터 정보
        num_queries: 생성할 질문 수 (기본 50개)
    
    Returns:
        [{"query": "...", "query_type": "..."}, ...] 리스트
    """
    topic = extract_topic_from_cluster(cluster_info)
    verbs = extract_verbs_from_cluster(cluster_info)
    
    # 키워드 리스트
    keywords = []
    if cluster_info.get("top_keywords"):
        for kw_item in cluster_info["top_keywords"][:10]:
            if isinstance(kw_item, dict):
                keywords.append(kw_item.get("keyword", ""))
            elif isinstance(kw_item, tuple):
                keywords.append(kw_item[0])
            else:
                keywords.append(str(kw_item))
    
    queries = []
    
    # 각 질문 타입별로 생성
    for query_type, templates in QUERY_TEMPLATES.items():
        num_per_type = num_queries // len(QUERY_TEMPLATES)  # 각 타입당 균등 분배
        
        for template in templates[:num_per_type]:
            # 템플릿 변수 치환
            verb = verbs[0] if verbs else "organize"
            alternative = keywords[1] if len(keywords) > 1 else "alternative"
            use_case = keywords[2] if len(keywords) > 2 else "home"
            
            try:
                query = template.format(
                    topic=topic,
                    verb=verb,
                    alternative=alternative,
                    use_case=use_case
                )
            except KeyError:
                # 템플릿에 없는 변수는 기본값으로 대체
                query = template.format(
                    topic=topic,
                    verb=verb,
                    alternative=alternative if '{alternative}' in template else topic,
                    use_case=use_case if '{use_case}' in template else "home"
                )
            
            # 중복 제거
            if query not in [q["query"] for q in queries]:
                queries.append({
                    "query": query,
                    "query_type": query_type
                })
            
            if len(queries) >= num_queries:
                break
        
        if len(queries) >= num_queries:
            break
    
    # 키워드 기반 추가 질문 생성
    for keyword in keywords[:10]:
        if len(queries) >= num_queries:
            break
        
        # 키워드 기반 질문
        keyword_queries = [
            f"best {keyword}",
            f"how to {keyword}",
            f"{keyword} tips",
            f"{keyword} guide",
            f"{keyword} ideas"
        ]
        
        for q in keyword_queries:
            if len(queries) >= num_queries:
                break
            if q not in [existing["query"] for existing in queries]:
                queries.append({
                    "query": q,
                    "query_type": "info_search"
                })
    
    return queries[:num_queries]


def save_cluster_queries(
    cluster_id: int,
    queries: List[Dict[str, str]],
    run_id: int
) -> int:
    """
    클러스터 질문을 DB에 저장
    
    Args:
        cluster_id: 클러스터 ID
        queries: 질문 리스트
        run_id: Pipeline run ID
    
    Returns:
        저장된 질문 수
    """
    conn = None
    saved_count = 0
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for query_data in queries:
                query = query_data["query"]
                query_type = query_data.get("query_type", "info_search")
                
                try:
                    cur.execute("""
                        INSERT INTO cluster_serp_queries (
                            cluster_id, query, query_type
                        ) VALUES (%s, %s, %s)
                        ON CONFLICT (cluster_id, query) DO NOTHING
                    """, (cluster_id, query, query_type))
                    
                    if cur.rowcount > 0:
                        saved_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save query '{query}': {e}")
                    continue
            
            conn.commit()
    
    finally:
        if conn:
            put_db_connection(conn)
    
    return saved_count


def generate_serp_queries_for_all_clusters(
    run_id: int,
    dry_run: bool = False,
    num_queries_per_cluster: int = 50
) -> Dict[str, Any]:
    """
    모든 클러스터에 대해 SERP 질문 생성
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
        num_queries_per_cluster: 클러스터당 질문 수 (기본 50개)
    
    Returns:
        Statistics dictionary
    """
    logger.info(f"Starting SERP query generation (run_id={run_id})")
    
    stats = {
        "clusters_processed": 0,
        "queries_generated": 0,
        "queries_saved": 0,
        "clusters": []
    }
    
    # 1. 클러스터 로드
    conn = None
    clusters_data = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.cluster_id, c.params_json, c.size
                FROM clusters c
                WHERE c.created_from_run_id = %s
                AND c.noise_label = FALSE
                ORDER BY c.cluster_id
            """, (run_id,))
            
            for cluster_id, params_json, size in cur.fetchall():
                # params_json에서 정보 추출
                params = params_json if isinstance(params_json, dict) else {}
                
                cluster_info = {
                    "cluster_id": cluster_id,
                    "category": params.get("category", ""),
                    "top_keywords": params.get("top_keywords", []),
                    "size": size
                }
                
                clusters_data.append(cluster_info)
    
    finally:
        if conn:
            put_db_connection(conn)
    
    if not clusters_data:
        logger.warning(f"No clusters found for run_id={run_id}")
        return stats
    
    logger.info(f"Found {len(clusters_data)} clusters")
    
    # 2. 각 클러스터별 질문 생성
    for cluster_info in clusters_data:
        cluster_id = cluster_info["cluster_id"]
        
        logger.info(f"Generating queries for cluster {cluster_id} ({cluster_info.get('category', 'unknown')})")
        
        queries = generate_queries_for_cluster(
            cluster_id,
            cluster_info,
            num_queries=num_queries_per_cluster
        )
        
        stats["queries_generated"] += len(queries)
        stats["clusters_processed"] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would generate {len(queries)} queries for cluster {cluster_id}:")
            for i, q in enumerate(queries[:5], 1):
                logger.info(f"  {i}. [{q['query_type']}] {q['query']}")
            if len(queries) > 5:
                logger.info(f"  ... and {len(queries) - 5} more")
        else:
            # DB에 저장
            saved = save_cluster_queries(cluster_id, queries, run_id)
            stats["queries_saved"] += saved
            
            logger.info(f"Generated {len(queries)} queries for cluster {cluster_id}, saved {saved}")
        
        stats["clusters"].append({
            "cluster_id": cluster_id,
            "queries_generated": len(queries),
            "queries": queries[:10]  # 샘플만 저장
        })
    
    logger.info(f"SERP query generation completed:")
    logger.info(f"  Clusters processed: {stats['clusters_processed']}")
    logger.info(f"  Queries generated: {stats['queries_generated']}")
    logger.info(f"  Queries saved: {stats['queries_saved']}")
    
    return stats
