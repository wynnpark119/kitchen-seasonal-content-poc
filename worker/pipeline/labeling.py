"""
LLM-based cluster labeling and Q&A brief generation with insights module

클러스터 단위로만 LLM 호출하여 topic_qa_briefs 생성
인사이트 모듈 6개 필드 추가: content_gap_analysis, execution_checklist, publishing_window,
format_recommendations, evidence_strength, safety_and_claims_flags
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI
from datetime import datetime
from .config import LLM_MODEL, LLM_MODEL_VERSION, LLM_MAX_RETRIES, LLM_TEMPERATURE, MAX_BRIEFS_TO_GENERATE
from .db import get_db_connection, upsert_topic_qa_brief
from .keywords import extract_keywords_for_cluster
from .scoring import get_top_clusters_for_briefs, calculate_trend_status_with_seasonality
from .timeseries import get_cluster_category
from .config import SEASONAL_CATEGORIES, EVERGREEN_CATEGORIES
from .models import TopicQABrief
from .logging import setup_logger

logger = setup_logger("labeling")

def build_llm_prompt(cluster_id: int, run_id: int) -> str:
    """
    Build LLM prompt from cluster data (토큰 최소화)
    
    입력 구성:
    - 대표 포스트 3~5개: title + 1~2문장 요약 + permalink + upvotes + month
    - 특징어 top 10~15
    - 월별 트렌드 요약 (짧은 요약)
    - GSC 요약 (있으면 상위 쿼리 5~10개 + 지표), 없으면 not available
    - SERP AIO 요약 (있으면 aio_text 요약 + cited_sources 5개), 없으면 NOT_AVAILABLE
    """
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            # Get representative samples (3-5개)
            cur.execute("""
                SELECT rp.title, rp.body, rp.upvotes, rp.permalink, rp.keyword,
                       DATE_TRUNC('month', TO_TIMESTAMP(rp.created_utc)) as month
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
            
            # Get monthly trends (최근 3개월, 짧은 요약)
            cur.execute("""
                SELECT month, reddit_post_count, reddit_weighted_score
                FROM cluster_timeseries
                WHERE cluster_id = %s
                AND created_from_run_id = %s
                ORDER BY month DESC
                LIMIT 6
            """, (cluster_id, run_id))
            
            trends = cur.fetchall()
            
            # 카테고리 및 시즌성 해석 정보
            category = get_cluster_category(cluster_id, run_id)
            is_seasonal = category in SEASONAL_CATEGORIES if category else False
            trend_status, trend_metadata = calculate_trend_status_with_seasonality(cluster_id, run_id)
            
            # Get GSC data (연관 키워드 상위 N개)
            cluster_keywords = keywords[:10] if keywords else []
            gsc_available = False
            gsc_summary = "not available"
            
            if cluster_keywords:
                cur.execute("""
                    SELECT query, SUM(impressions) as total_impressions, 
                           SUM(clicks) as total_clicks, AVG(ctr) as avg_ctr
                    FROM raw_gsc_queries
                    WHERE query ILIKE ANY(ARRAY[%s])
                    GROUP BY query
                    ORDER BY total_impressions DESC
                    LIMIT 10
                """, ([f"%{kw}%" for kw in cluster_keywords],))
                
                gsc_data = cur.fetchall()
                if gsc_data:
                    gsc_available = True
                    gsc_summary = f"Top queries: {', '.join([q[0] for q in gsc_data[:5]])}. "
                    gsc_summary += f"Total impressions: {sum(int(i) for _, i, _, _ in gsc_data):,}, "
                    gsc_summary += f"Total clicks: {sum(int(c) for _, _, c, _ in gsc_data):,}"
            
            # Get SERP AIO (관련 키워드의 AI Overview)
            serp_available = False
            serp_summary = "NOT_AVAILABLE"
            
            if cluster_keywords:
                cur.execute("""
                    SELECT query, aio_text, cited_sources_json, aio_status
                    FROM raw_serp_aio
                    WHERE query ILIKE ANY(ARRAY[%s])
                    AND aio_status = 'AVAILABLE'
                    ORDER BY snapshot_at DESC
                    LIMIT 1
                """, ([f"%{kw}%" for kw in cluster_keywords[:5]],))
                
                serp_result = cur.fetchone()
                if serp_result:
                    query, aio_text, cited_sources, aio_status = serp_result
                    if aio_status == 'AVAILABLE' and aio_text:
                        serp_available = True
                        aio_summary = (aio_text[:300] + "...") if len(aio_text) > 300 else aio_text
                        sources = cited_sources if cited_sources else []
                        sources_list = sources[:5] if isinstance(sources, list) else []
                        serp_summary = f"Query: '{query}'. Summary: {aio_summary}. "
                        serp_summary += f"Cited sources: {len(sources_list)} sources"
            
            # Build prompt (토큰 최소화)
            prompt = f"""Analyze this cluster of Reddit posts about kitchen lifestyle topics.

Representative Posts (3-5 samples):
"""
            for i, (title, body, upvotes, permalink, keyword, month) in enumerate(samples, 1):
                # 1-2문장 요약
                body_summary = ""
                if body:
                    sentences = body.split('.')[:2]
                    body_summary = '. '.join(s.strip() for s in sentences if s.strip())
                    if len(body_summary) > 150:
                        body_summary = body_summary[:150] + "..."
                
                month_str = month.strftime('%Y-%m') if month else "N/A"
                prompt += f"{i}. [{keyword}] {title}\n   Summary: {body_summary}\n   Upvotes: {upvotes}, Month: {month_str}\n\n"
            
            prompt += f"\nKey Keywords (top 15): {', '.join(keywords[:15])}\n\n"
            
            # 카테고리 및 시즌성 정보
            prompt += f"\nCategory Context:\n"
            if category:
                prompt += f"  Category: {category}\n"
                prompt += f"  Category Type: {'SEASONAL' if is_seasonal else 'EVERGREEN'}\n"
                if is_seasonal:
                    prompt += f"  Trend Interpretation: seasonality-adjusted\n"
                    if trend_metadata.get('spring_baseline'):
                        prompt += f"  Spring Baseline Score: {trend_metadata['spring_baseline']:.2f}\n"
                    if trend_metadata.get('spring_adjusted_lift') is not None:
                        prompt += f"  Spring Adjusted Lift: {trend_metadata['spring_adjusted_lift']:.2%}\n"
                else:
                    prompt += f"  Trend Interpretation: non-seasonal (absolute growth)\n"
            else:
                prompt += f"  Category: unknown (infer from content)\n"
            
            prompt += f"  Trend Status: {trend_status}\n"
            if trend_metadata.get('interpretation'):
                prompt += f"  Trend Details: {trend_metadata['interpretation']}\n"
            prompt += "\n"
            
            # 월별 트렌드 요약 (최근 3개월)
            if trends:
                prompt += "Monthly Trends (Reddit, recent 3 months):\n"
                trend_summary = []
                for month, count, score in trends[:3]:
                    month_str = month.strftime('%Y-%m') if month else "N/A"
                    trend_summary.append(f"{month_str}: {count} posts, score={float(score or 0):.2f}")
                prompt += " - ".join(trend_summary) + "\n\n"
            else:
                prompt += "Monthly Trends: not enough data\n\n"
            
            # GSC 요약
            prompt += f"Google Search Console: {gsc_summary}\n\n"
            
            # SERP AIO 요약
            prompt += f"SERP AI Overview: {serp_summary}\n\n"
            
            # Why-now 생성 규칙 명시
            why_now_rule = ""
            if is_seasonal:
                why_now_rule = """
IMPORTANT: For why_now field:
- DO NOT use "봄이라서" (because it's spring) as the sole explanation
- MUST include "기대 대비 초과/미달" (outperformance/underperformance vs baseline) evidence
- If trend_status is SEASONAL_OUTPERFORM: explain why it's exceeding spring expectations
- If trend_status is SEASONAL_UNDERPERFORM: explain why it's underperforming despite spring season
- If trend_status is SEASONAL_EXPECTED: explain what makes this normal spring pattern interesting
"""
            else:
                why_now_rule = """
IMPORTANT: For why_now field:
- Use absolute growth / recent weighted increase as primary evidence
- Season (spring) can be mentioned as secondary context only (e.g., "spring lifestyle reset")
- Focus on: EMERGING (recent surge), STEADY (sustained interest), or DECLINING (declining interest) patterns
"""
            
            prompt += f"""{why_now_rule}

Provide a JSON response with this structure:
{{
  "category": "One of: SPRING_RECIPES, SPRING_KITCHEN_STYLING, REFRIGERATOR_ORGANIZATION, VEGETABLE_PREP_HANDLING",
  "topic_title": "Topic title in Korean (max 500 chars)",
  "primary_question": "Primary question in Korean",
  "related_questions": ["Question 1", "Question 2", ...],  // 3-7 questions
  "blog_angle": "Blog content angle in Korean (title/outline/target_query)",
  "social_angle": "Social media content angle in Korean (hook/post ideas/hashtags)",
  "why_now": {{
    "trend_summary": "...",  // Follow the IMPORTANT rules above
    "drivers": ["driver1", "driver2", ...],
    "expected_impact": "..."
  }},
  "evidence_pack": {{
    "reddit_summary": "...",
    "gsc_summary": "...",
    "serp_aio_summary": "..."
  }},
  "risks_and_notes": "...",
  "output_version": "1.0",
  "insights": {{
    "content_gap_analysis": {{
      "aio_coverage": "...",  // AIO가 다루는 포인트 요약 (있으면) 또는 "AIO 미노출" (없으면)
      "differentiation_points": ["point1", "point2", "point3"],  // 차별화 포인트 3개
      "content_opportunities": ["opportunity1", "opportunity2"]  // AIO 없으면 기회 가설 2-3개
    }},
    "execution_checklist": [
      "Step 1: ...",
      "Step 2: ...",
      ...
    ],  // 6-10 steps
    "publishing_window": {{
      "recommended_window": "YYYY-MM ~ YYYY-MM",  // 2-6주 권장 또는 "not enough signal"
      "rationale": "왜 지금인지 한 문장"
    }},
    "format_recommendations": {{
      "blog_format": "how-to | listicle | myth-busting | checklist | before-after",
      "social_format": "carousel | short video | story | pin-style",
      "rationale": "선택 근거 1-2문장"
    }},
    "evidence_strength": {{
      "score": 0-100,
      "drivers": ["driver1", "driver2", ...]  // 3-5개
    }},
    "safety_and_claims_flags": {{
      "flags": ["flag1", "flag2", ...],  // 없으면 빈 배열
      "recommended_disclaimer": "..."  // 없으면 빈 문자열
    }}
  }}
}}
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
                    {"role": "system", "content": "You are a content strategist analyzing kitchen lifestyle topics. Always respond with valid JSON only. Never make up data - if GSC or AIO is not available, explicitly state 'not available' or 'NOT_AVAILABLE'."},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLM_TEMPERATURE,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate basic structure
            brief = TopicQABrief(**{k: v for k, v in result.items() if k != "insights"})
            
            # Extract insights separately
            insights = result.get("insights", {})
            
            return {
                **brief.model_dump(),
                "insights": insights
            }
        
        except Exception as e:
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_attempts}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"LLM call failed after {max_attempts} attempts: {e}")
                raise

def build_evidence_pack(cluster_id: int, run_id: int) -> Dict[str, Any]:
    """
    Build evidence pack for cluster (Reddit + GSC + SERP AIO)
    
    GSC/AIO 없으면 "not available" 명시 (추론 금지)
    """
    conn = get_db_connection()
    evidence = {
        "reddit_posts": [],
        "reddit_comments": [],
        "gsc_data": "not available",
        "serp_aio": "NOT_AVAILABLE"
    }
    
    try:
        with conn.cursor() as cur:
            # Get top Reddit posts (3-5개)
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
            
            # Get top comments for representative posts
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
                    if len(comments_by_post[post_id]) < 3:
                        comments_by_post[post_id].append({
                            "body": (body[:150] + "...") if body and len(body) > 150 else (body or ""),
                            "upvotes": upvotes,
                            "author": author
                        })
                
                evidence["reddit_comments"] = comments_by_post
            
            # Get GSC data (있으면)
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
                if gsc_queries:
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
            
            # Get SERP AIO (있으면)
            if cluster_keywords:
                cur.execute("""
                    SELECT query, aio_text, cited_sources_json, snapshot_at, aio_status
                    FROM raw_serp_aio
                    WHERE query ILIKE ANY(ARRAY[%s])
                    AND aio_status = 'AVAILABLE'
                    ORDER BY snapshot_at DESC
                    LIMIT 1
                """, ([f"%{kw}%" for kw in cluster_keywords[:3]],))
                
                serp_result = cur.fetchone()
                if serp_result:
                    query, aio_text, cited_sources, snapshot_at, aio_status = serp_result
                    if aio_status == 'AVAILABLE' and aio_text:
                        evidence["serp_aio"] = {
                            "query": query,
                            "aio_summary": (aio_text[:300] + "...") if aio_text and len(aio_text) > 300 else (aio_text or ""),
                            "cited_sources": cited_sources if cited_sources else [],
                            "snapshot_at": snapshot_at.isoformat() if snapshot_at else None
                        }
    
    finally:
        conn.close()
    
    return evidence

def generate_briefs(run_id: int, dry_run: bool = False, max_briefs: int = MAX_BRIEFS_TO_GENERATE) -> Dict[str, Any]:
    """
    Generate Q&A briefs for top N clusters (우선순위 점수 기반)
    
    카테고리별 시즌성 해석 로직 적용
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
        max_briefs: Maximum number of briefs to generate (default: MAX_BRIEFS_TO_GENERATE)
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key and not dry_run:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    if not dry_run:
        client = OpenAI(api_key=openai_key)
    
    stats = {
        "clusters_processed": 0,
        "briefs_created": 0,
        "errors": []
    }
    
    # Get top clusters by priority score (trend_metadata 포함)
    top_clusters = get_top_clusters_for_briefs(run_id, max_briefs)
    
    logger.info(f"Generating briefs for top {len(top_clusters)} clusters (max_briefs={max_briefs})")
    
    for cluster_id, score, trend_status, trend_metadata in top_clusters:
        try:
            if dry_run:
                category = trend_metadata.get('category', 'unknown')
                if stats["clusters_processed"] < 3:
                    logger.info(f"[DRY RUN] Would generate brief for cluster {cluster_id} ({category}, score: {score:.2f}, status: {trend_status})")
                stats["clusters_processed"] += 1
                continue
            
            # Build prompt
            prompt = build_llm_prompt(cluster_id, run_id)
            
            # Call LLM
            brief_data = call_llm(prompt, client)
            
            # Extract insights
            insights = brief_data.pop("insights", {})
            
            # Build evidence pack
            evidence = build_evidence_pack(cluster_id, run_id)
            brief_data["evidence_pack"] = evidence
            
            # Add risks_and_notes if not present
            if "risks_and_notes" not in brief_data:
                brief_data["risks_and_notes"] = ""
            
            # Add output_version if not present
            if "output_version" not in brief_data:
                brief_data["output_version"] = "1.0"
            
            # Save brief with insights_json
            upsert_topic_qa_brief(
                brief_data=brief_data,
                cluster_id=cluster_id,
                model_name=LLM_MODEL,
                model_version=LLM_MODEL_VERSION,
                run_id=run_id,
                insights_json=insights
            )
            
            stats["briefs_created"] += 1
            stats["clusters_processed"] += 1
            
            category = trend_metadata.get('category', 'unknown')
            logger.info(f"Brief created for cluster {cluster_id} ({category}, score: {score:.2f}, trend: {trend_status})")
            
            # Rate limiting
            time.sleep(1)
        
        except Exception as e:
            logger.error(f"Error generating brief for cluster {cluster_id}: {e}")
            stats["errors"].append(str(e))
    
    logger.info(f"Brief generation completed: {stats['briefs_created']} briefs created")
    return stats
