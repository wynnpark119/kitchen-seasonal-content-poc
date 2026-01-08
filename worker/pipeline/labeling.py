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
    """Build LLM prompt from cluster data"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            # Get representative samples
            cur.execute("""
                SELECT rp.title, rp.body, rp.upvotes, rp.permalink
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
                AND ca.is_representative = TRUE
                ORDER BY rp.upvotes DESC
                LIMIT 5
            """, (cluster_id, run_id))
            
            samples = cur.fetchall()
            
            # Get keywords
            keywords = extract_keywords_for_cluster(cluster_id, run_id)
            
            # Get monthly trends
            cur.execute("""
                SELECT month, reddit_post_count, reddit_weighted_score
                FROM cluster_timeseries
                WHERE cluster_id = %s
                AND created_from_run_id = %s
                ORDER BY month DESC
                LIMIT 3
            """, (cluster_id, run_id))
            
            trends = cur.fetchall()
            
            # Build prompt
            prompt = f"""Analyze this cluster of Reddit posts about kitchen lifestyle topics.

Representative Posts:
"""
            for i, (title, body, upvotes, permalink) in enumerate(samples, 1):
                prompt += f"{i}. {title}\n   {body[:200]}...\n   Upvotes: {upvotes}\n\n"
            
            prompt += f"\nKey Keywords: {', '.join(keywords[:15])}\n\n"
            
            if trends:
                prompt += "Monthly Trends:\n"
                for month, count, score in trends:
                    prompt += f"- {month}: {count} posts, {score:.0f} total upvotes\n"
            
            prompt += """
Please provide a JSON response with the following structure:
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
    """Call LLM with retry logic"""
    for attempt in range(LLM_MAX_RETRIES):
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
            if attempt < LLM_MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                logger.warning(f"LLM call failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise

def build_evidence_pack(cluster_id: int, run_id: int) -> Dict[str, Any]:
    """Build evidence pack for cluster"""
    conn = get_db_connection()
    evidence = {
        "reddit_posts": [],
        "gsc_data": {},
        "serp_aio": None
    }
    
    try:
        with conn.cursor() as cur:
            # Get top Reddit posts
            cur.execute("""
                SELECT rp.title, rp.body, rp.upvotes, rp.permalink, rp.url
                FROM raw_reddit_posts rp
                JOIN cluster_assignments ca ON ca.doc_id = rp.reddit_post_id
                WHERE ca.cluster_id = %s
                AND ca.created_from_run_id = %s
                ORDER BY rp.upvotes DESC
                LIMIT 5
            """, (cluster_id, run_id))
            
            for title, body, upvotes, permalink, url in cur.fetchall():
                evidence["reddit_posts"].append({
                    "title": title,
                    "summary": body[:200] + "..." if len(body) > 200 else body,
                    "upvotes": upvotes,
                    "link": f"https://reddit.com{permalink}" if permalink else url
                })
            
            # Get GSC data (simplified - could be more sophisticated)
            cur.execute("""
                SELECT query, SUM(impressions) as total_impressions, SUM(clicks) as total_clicks
                FROM raw_gsc_queries
                GROUP BY query
                ORDER BY total_impressions DESC
                LIMIT 10
            """)
            
            gsc_data = cur.fetchall()
            evidence["gsc_data"] = {
                "top_queries": [{"query": q, "impressions": i, "clicks": c} for q, i, c in gsc_data]
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
