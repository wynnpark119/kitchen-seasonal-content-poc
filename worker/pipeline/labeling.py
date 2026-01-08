"""
LLM-based cluster labeling and Q&A brief generation
"""
import os
import json
import time
from typing import Dict, Any, List
from openai import OpenAI
from .config import LLM_MODEL, LLM_MODEL_VERSION, LLM_MAX_RETRIES, LLM_TEMPERATURE, MAX_BRIEFS_TO_GENERATE
from .db import get_db_connection, upsert_topic_qa_brief
from .keywords import extract_keywords_for_cluster
from .models import TopicQABrief
from .logging import setup_logger

logger = setup_logger("labeling")

def build_llm_prompt(cluster_id: int, run_id: int) -> str:
    """Build LLM prompt from cluster data (대표 샘플 + 특징어 + 트렌드 + GSC + SERP AIO)"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            # Get representative samples (3-5개)
            cur.execute("""
                SELECT rp.title, rp.body, rp.upvotes, rp.permalink, rp.keyword
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
                AND ca.is_representative = TRUE
                ORDER BY rp.upvotes DESC
                LIMIT 5
            """, (cluster_id, run_id))
            
            samples = cur.fetchall()
            
            # Get keywords (top 10-15)
            keywords = extract_keywords_for_cluster(cluster_id, run_id)
            
            # Get monthly trends (최근 3개월)
            cur.execute("""
                SELECT month, reddit_post_count, reddit_weighted_score
                FROM cluster_timeseries
                WHERE cluster_id = %s
                AND created_from_run_id = %s
                ORDER BY month DESC
                LIMIT 3
            """, (cluster_id, run_id))
            
            trends = cur.fetchall()
            
            # Get GSC data (연관 키워드 상위 N개)
            # 클러스터의 키워드와 관련된 GSC 쿼리 찾기
            cluster_keywords_str = "|".join(keywords[:10])
            cur.execute("""
                SELECT query, SUM(impressions) as total_impressions, 
                       SUM(clicks) as total_clicks, AVG(ctr) as avg_ctr
                FROM raw_gsc_queries
                WHERE query ILIKE ANY(ARRAY[%s])
                GROUP BY query
                ORDER BY total_impressions DESC
                LIMIT 10
            """, ([f"%{kw}%" for kw in keywords[:10]],))
            
            gsc_data = cur.fetchall()
            
            # Get SERP AIO (관련 키워드의 AI Overview)
            cur.execute("""
                SELECT query, aio_text, cited_sources_json
                FROM raw_serp_aio
                WHERE query ILIKE ANY(ARRAY[%s])
                ORDER BY snapshot_at DESC
                LIMIT 1
            """, ([f"%{kw}%" for kw in keywords[:5]],))
            
            serp_aio = cur.fetchone()
            
            # Build prompt (토큰 최소화)
            prompt = f"""Analyze this cluster of Reddit posts about kitchen lifestyle topics.

Representative Posts (3-5 samples):
"""
            for i, (title, body, upvotes, permalink, keyword) in enumerate(samples, 1):
                body_summary = body[:150] + "..." if body and len(body) > 150 else (body or "")
                prompt += f"{i}. [{keyword}] {title}\n   {body_summary}\n   Upvotes: {upvotes}\n\n"
            
            prompt += f"\nKey Keywords (top 15): {', '.join(keywords[:15])}\n\n"
            
            if trends:
                prompt += "Monthly Trends (Reddit):\n"
                for month, count, score in trends:
                    prompt += f"- {month.strftime('%Y-%m')}: {count} posts, {score:.0f} total upvotes\n"
                prompt += "\n"
            
            if gsc_data:
                prompt += "Google Search Console (Top queries):\n"
                for query, impressions, clicks, ctr in gsc_data[:5]:
                    prompt += f"- '{query}': {impressions} impressions, {clicks} clicks, {ctr:.2%} CTR\n"
                prompt += "\n"
            
            if serp_aio:
                query, aio_text, cited_sources = serp_aio
                prompt += f"SERP AI Overview (query: '{query}'):\n"
                prompt += f"{aio_text[:300]}...\n\n"
            
            prompt += """
Provide a JSON response with this structure:
{
  "category": "One of: SPRING_RECIPES, SPRING_KITCHEN_STYLING, REFRIGERATOR_ORGANIZATION, VEGETABLE_PREP_HANDLING",
  "topic_title": "Topic title in Korean (max 500 chars)",
  "primary_question": "Primary question in Korean",
  "related_questions": ["Question 1", "Question 2", ...],
  "blog_angle": "Blog content angle in Korean",
  "social_angle": "Social media content angle in Korean",
  "why_now": {"reason": "...", "trend": "..."},
  "evidence_summary": "Summary of evidence in Korean"
}
"""
            return prompt
    
    finally:
        conn.close()

def call_llm(prompt: str, client: OpenAI) -> Dict[str, Any]:
    """Call LLM with retry logic (최대 2회 재시도)"""
    max_attempts = LLM_MAX_RETRIES + 1  # 초기 시도 + 재시도 횟수
    
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a content strategist analyzing kitchen lifestyle topics. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLM_TEMPERATURE,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate with Pydantic
            brief = TopicQABrief(**result)
            return brief.model_dump()
        
        except Exception as e:
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_attempts}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"LLM call failed after {max_attempts} attempts: {e}")
                raise

def build_evidence_pack(cluster_id: int, run_id: int) -> Dict[str, Any]:
    """Build evidence pack for cluster (Reddit + GSC + SERP AIO)"""
    conn = get_db_connection()
    evidence = {
        "reddit_posts": [],
        "reddit_comments": [],
        "gsc_data": {},
        "serp_aio": None
    }
    
    try:
        with conn.cursor() as cur:
            # Get top Reddit posts (3-5개, 제목/요약/링크/업보트)
            cur.execute("""
                SELECT rp.reddit_post_id, rp.title, rp.body, rp.upvotes, 
                       rp.permalink, rp.url, rp.keyword
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
                ORDER BY rp.upvotes DESC
                LIMIT 5
            """, (cluster_id, run_id))
            
            post_ids = []
            for post_id, title, body, upvotes, permalink, url, keyword in cur.fetchall():
                post_ids.append(post_id)
                evidence["reddit_posts"].append({
                    "title": title,
                    "summary": (body[:200] + "...") if body and len(body) > 200 else (body or ""),
                    "link": f"https://reddit.com{permalink}" if permalink else (url or ""),
                    "upvotes": upvotes,
                    "keyword": keyword
                })
            
            # Get top comments for representative posts (각 포스트당 Top 1-3)
            if post_ids:
                cur.execute("""
                    SELECT rc.reddit_post_id, rc.body, rc.upvotes, rc.author
                    FROM raw_reddit_comments rc
                    WHERE rc.reddit_post_id = ANY(%s)
                    AND rc.is_top = TRUE
                    ORDER BY rc.reddit_post_id, rc.upvotes DESC
                """, (post_ids,))
                
                comments_by_post = {}
                for post_id, body, upvotes, author in cur.fetchall():
                    if post_id not in comments_by_post:
                        comments_by_post[post_id] = []
                    if len(comments_by_post[post_id]) < 3:  # Top 3 per post
                        comments_by_post[post_id].append({
                            "body": (body[:150] + "...") if body and len(body) > 150 else (body or ""),
                            "upvotes": upvotes,
                            "author": author
                        })
                
                evidence["reddit_comments"] = comments_by_post
            
            # Get GSC data (연관 키워드 상위 N개, 월별 impressions/clicks/ctr/position 요약)
            # 클러스터의 키워드와 매칭되는 GSC 쿼리 찾기
            cur.execute("""
                SELECT DISTINCT keyword
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
                LIMIT 5
            """, (cluster_id, run_id))
            
            cluster_keywords = [row[0] for row in cur.fetchall()]
            
            if cluster_keywords:
                keywords_pattern = "|".join(cluster_keywords)
                cur.execute("""
                    SELECT query, 
                           SUM(impressions) as total_impressions,
                           SUM(clicks) as total_clicks,
                           AVG(ctr) as avg_ctr,
                           AVG(position) as avg_position
                    FROM raw_gsc_queries
                    WHERE query ILIKE ANY(ARRAY[%s])
                    GROUP BY query
                    ORDER BY total_impressions DESC
                    LIMIT 10
                """, ([f"%{kw}%" for kw in cluster_keywords],))
                
                gsc_queries = cur.fetchall()
                evidence["gsc_data"] = {
                    "top_queries": [
                        {
                            "query": q,
                            "impressions": int(i),
                            "clicks": int(c),
                            "ctr": float(ctr) if ctr else 0.0,
                            "avg_position": float(pos) if pos else None
                        }
                        for q, i, c, ctr, pos in gsc_queries
                    ],
                    "summary": {
                        "total_queries": len(gsc_queries),
                        "total_impressions": sum(int(i) for _, i, _, _, _ in gsc_queries),
                        "total_clicks": sum(int(c) for _, _, c, _, _ in gsc_queries)
                    }
                }
            
            # Get SERP AIO (해당 카테고리/쿼리 묶음에 대한 참고)
            if cluster_keywords:
                cur.execute("""
                    SELECT query, aio_text, cited_sources_json, snapshot_at
                    FROM raw_serp_aio
                    WHERE query ILIKE ANY(ARRAY[%s])
                    ORDER BY snapshot_at DESC
                    LIMIT 1
                """, ([f"%{kw}%" for kw in cluster_keywords[:3]],))
                
                serp_result = cur.fetchone()
                if serp_result:
                    query, aio_text, cited_sources, snapshot_at = serp_result
                    evidence["serp_aio"] = {
                        "query": query,
                        "aio_summary": (aio_text[:300] + "...") if aio_text and len(aio_text) > 300 else (aio_text or ""),
                        "cited_sources": cited_sources if cited_sources else [],
                        "snapshot_at": snapshot_at.isoformat() if snapshot_at else None
                    }
    
    finally:
        conn.close()
    
    return evidence

def generate_briefs(run_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Generate Q&A briefs for clusters"""
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    client = OpenAI(api_key=openai_key)
    
    conn = get_db_connection()
    stats = {
        "clusters_processed": 0,
        "briefs_created": 0,
        "errors": []
    }
    
    try:
        with conn.cursor() as cur:
            # Get top clusters by size
            cur.execute("""
                SELECT cluster_id, size
                FROM clusters
                WHERE created_from_run_id = %s
                AND noise_label = FALSE
                ORDER BY size DESC
                LIMIT %s
            """, (run_id, MAX_BRIEFS_TO_GENERATE))
            
            clusters = cur.fetchall()
            logger.info(f"Generating briefs for {len(clusters)} clusters")
            
            for cluster_id, size in clusters:
                try:
                    if dry_run:
                        if stats["clusters_processed"] < 3:
                            logger.info(f"[DRY RUN] Would generate brief for cluster {cluster_id} (size: {size})")
                        stats["clusters_processed"] += 1
                        continue
                    
                    # Build prompt
                    prompt = build_llm_prompt(cluster_id, run_id)
                    
                    # Call LLM
                    brief_data = call_llm(prompt, client)
                    
                    # Build evidence pack
                    evidence = build_evidence_pack(cluster_id, run_id)
                    brief_data["evidence_pack"] = evidence
                    
                    # Save brief
                    upsert_topic_qa_brief(
                        brief_data=brief_data,
                        cluster_id=cluster_id,
                        model_name=LLM_MODEL,
                        model_version=LLM_MODEL_VERSION,
                        run_id=run_id
                    )
                    
                    stats["briefs_created"] += 1
                    stats["clusters_processed"] += 1
                    
                    # Rate limiting
                    time.sleep(1)
                
                except Exception as e:
                    logger.error(f"Error generating brief for cluster {cluster_id}: {e}")
                    stats["errors"].append(str(e))
    
    finally:
        conn.close()
    
    logger.info(f"Brief generation completed: {stats['briefs_created']} briefs created")
    return stats
