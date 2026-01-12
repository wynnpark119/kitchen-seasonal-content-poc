"""
클러스터 요약만 임베딩 생성

Reddit post 전체나 SERP raw에 임베딩 금지
각 클러스터별 요약 텍스트만 임베딩
"""
import os
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError
import random

from .db import get_db_connection, put_db_connection
from .config import EMBEDDING_MODEL, EMBEDDING_DIM, API_MAX_RETRIES, API_BACKOFF_FACTOR
from .embedding import truncate_text_to_max_tokens
from .logging import setup_logger

logger = setup_logger("cluster_embedding")

MAX_TOKENS = 8192


def build_cluster_embedding_text(
    summary: str,
    top_keywords: List[str],
    serp_snippets: Optional[List[str]] = None
) -> str:
    """
    클러스터 임베딩용 텍스트 생성
    
    Args:
        summary: 클러스터 요약 텍스트
        top_keywords: 상위 키워드 리스트
        serp_snippets: 대표 SERP snippet 일부 (선택적)
    
    Returns:
        임베딩용 텍스트
    """
    parts = []
    
    # 1. 요약 텍스트
    if summary:
        parts.append(summary)
    
    # 2. 상위 키워드
    if top_keywords:
        keywords_str = ", ".join(top_keywords[:20])
        parts.append(f"\n\nKey topics: {keywords_str}")
    
    # 3. SERP snippet (선택적, 최대 2개)
    if serp_snippets:
        for i, snippet in enumerate(serp_snippets[:2], 1):
            if snippet:
                truncated_snippet = snippet[:200]  # 각 snippet 최대 200자
                parts.append(f"\n\nRelated content {i}: {truncated_snippet}")
    
    text = "".join(parts)
    
    # 토큰 제한 적용
    return truncate_text_to_max_tokens(text, MAX_TOKENS)


def generate_cluster_embedding(
    text: str,
    client: OpenAI,
    max_retries: int = 3
) -> Optional[List[float]]:
    """
    클러스터 텍스트에 대한 임베딩 생성 (재시도 포함)
    
    Args:
        text: 임베딩할 텍스트
        client: OpenAI client
        max_retries: 최대 재시도 횟수
    
    Returns:
        임베딩 벡터 또는 None (실패 시)
    """
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            
            if response.data and len(response.data) > 0:
                return response.data[0].embedding
            
            return None
        
        except (RateLimitError, APIConnectionError, APITimeoutError) as e:
            if attempt < max_retries - 1:
                wait_time = (API_BACKOFF_FACTOR ** attempt) + random.uniform(0, 1)
                logger.warning(f"Transient error in cluster embedding (attempt {attempt + 1}/{max_retries}), retrying in {wait_time:.2f}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to generate cluster embedding after {max_retries} attempts: {e}")
                return None
        
        except APIError as e:
            # Permanent 에러 (토큰 초과 등)
            error_code = getattr(e, 'code', None) or str(e.type) if hasattr(e, 'type') else None
            if error_code and 'invalid_request' in str(error_code).lower():
                logger.error(f"Permanent error in cluster embedding (no retry): {e}")
                return None
            
            # 기타 API 에러는 재시도
            if attempt < max_retries - 1:
                wait_time = (API_BACKOFF_FACTOR ** attempt) + random.uniform(0, 1)
                logger.warning(f"API error in cluster embedding (attempt {attempt + 1}/{max_retries}), retrying in {wait_time:.2f}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to generate cluster embedding after {max_retries} attempts: {e}")
                return None
        
        except Exception as e:
            logger.error(f"Unexpected error in cluster embedding: {e}")
            return None
    
    return None


def save_cluster_embedding(
    cluster_id: int,
    embedding: List[float],
    run_id: int
) -> bool:
    """
    클러스터 임베딩을 DB에 저장
    
    Args:
        cluster_id: 클러스터 ID
        embedding: 임베딩 벡터
        run_id: Pipeline run ID
    
    Returns:
        성공 여부
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            from psycopg2.extras import Json as PsycopgJson
            
            cur.execute("""
                INSERT INTO cluster_embeddings (
                    cluster_id, embedding_json, model_name, dim, created_from_run_id
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cluster_id, created_from_run_id) DO UPDATE SET
                    embedding_json = EXCLUDED.embedding_json,
                    model_name = EXCLUDED.model_name,
                    dim = EXCLUDED.dim
            """, (
                cluster_id,
                PsycopgJson(embedding),
                EMBEDDING_MODEL,
                EMBEDDING_DIM,
                run_id
            ))
            
            conn.commit()
            return True
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to save cluster embedding for cluster {cluster_id}: {e}")
        return False
    
    finally:
        if conn:
            put_db_connection(conn)


def generate_embeddings_for_all_clusters(
    run_id: int,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    모든 클러스터에 대해 임베딩 생성
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
    
    Returns:
        Statistics dictionary
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key and not dry_run:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    if not dry_run:
        client = OpenAI(api_key=openai_key)
    
    logger.info(f"Starting cluster embedding generation (run_id={run_id})")
    
    stats = {
        "clusters_processed": 0,
        "embeddings_created": 0,
        "embeddings_failed": 0,
        "errors": []
    }
    
    # 1. 클러스터 정보 로드
    conn = None
    clusters_data = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.cluster_id, c.params_json
                FROM clusters c
                WHERE c.created_from_run_id = %s
                AND c.noise_label = FALSE
                ORDER BY c.cluster_id
            """, (run_id,))
            
            for cluster_id, params_json in cur.fetchall():
                params = params_json if isinstance(params_json, dict) else {}
                
                # SERP snippet 가져오기 (선택적)
                cur.execute("""
                    SELECT snippet
                    FROM serp_results
                    WHERE cluster_id = %s
                    AND snippet IS NOT NULL
                    ORDER BY position ASC
                    LIMIT 2
                """, (cluster_id,))
                
                serp_snippets = [row[0] for row in cur.fetchall() if row[0]]
                
                clusters_data.append({
                    "cluster_id": cluster_id,
                    "summary": params.get("summary", ""),
                    "top_keywords": params.get("top_keywords", []),
                    "serp_snippets": serp_snippets
                })
    
    finally:
        if conn:
            put_db_connection(conn)
    
    if not clusters_data:
        logger.warning(f"No clusters found for run_id={run_id}")
        return stats
    
    logger.info(f"Found {len(clusters_data)} clusters to embed")
    
    # 2. 각 클러스터별 임베딩 생성
    for cluster_info in clusters_data:
        cluster_id = cluster_info["cluster_id"]
        
        # 키워드 리스트 변환
        top_keywords = []
        if cluster_info.get("top_keywords"):
            for kw_item in cluster_info["top_keywords"]:
                if isinstance(kw_item, dict):
                    top_keywords.append(kw_item.get("keyword", ""))
                elif isinstance(kw_item, tuple):
                    top_keywords.append(kw_item[0])
                else:
                    top_keywords.append(str(kw_item))
        
        # 임베딩용 텍스트 생성
        embedding_text = build_cluster_embedding_text(
            summary=cluster_info.get("summary", ""),
            top_keywords=top_keywords,
            serp_snippets=cluster_info.get("serp_snippets")
        )
        
        logger.info(f"Processing cluster {cluster_id} (text length: {len(embedding_text)} chars)")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would generate embedding for cluster {cluster_id}")
            logger.info(f"[DRY RUN] Text preview: {embedding_text[:200]}...")
            stats["embeddings_created"] += 1
        else:
            # 임베딩 생성
            embedding = generate_cluster_embedding(embedding_text, client)
            
            if embedding:
                # DB에 저장
                success = save_cluster_embedding(cluster_id, embedding, run_id)
                
                if success:
                    stats["embeddings_created"] += 1
                    logger.info(f"✅ Created embedding for cluster {cluster_id}")
                else:
                    stats["embeddings_failed"] += 1
                    stats["errors"].append(f"cluster_{cluster_id}: save_failed")
            else:
                stats["embeddings_failed"] += 1
                stats["errors"].append(f"cluster_{cluster_id}: embedding_generation_failed")
                logger.error(f"❌ Failed to generate embedding for cluster {cluster_id}")
        
        stats["clusters_processed"] += 1
    
    logger.info(f"Cluster embedding generation completed:")
    logger.info(f"  Clusters processed: {stats['clusters_processed']}")
    logger.info(f"  Embeddings created: {stats['embeddings_created']}")
    logger.info(f"  Embeddings failed: {stats['embeddings_failed']}")
    
    return stats
