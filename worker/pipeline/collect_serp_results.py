"""
SERP API 수집/적재 파이프라인

클러스터별 질문에 대해 Google 검색 결과 수집
"""
import os
import time
import random
import re
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse
from serpapi import GoogleSearch
from .db import get_db_connection, put_db_connection
from .logging import setup_logger

logger = setup_logger("collect_serp_results")

# 재시도 설정
MAX_RETRIES = 3
RETRY_BACKOFF = 2
REQUEST_TIMEOUT = 30  # 초
RATE_LIMIT_DELAY = 1.0  # 초


def extract_domain(url: str) -> str:
    """URL에서 도메인 추출"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace('www.', '')
    except:
        return ""


def deduplicate_urls(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    중복 URL 제거
    
    Args:
        results: 검색 결과 리스트
    
    Returns:
        중복 제거된 결과 리스트
    """
    seen_urls: Set[str] = set()
    deduplicated = []
    
    for result in results:
        url = result.get("url", "").lower().strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduplicated.append(result)
    
    return deduplicated


def fetch_serp_results(
    query: str,
    serpapi_key: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    SERP API로 검색 결과 가져오기
    
    Args:
        query: 검색 질문
        serpapi_key: SerpAPI 키
        max_results: 최대 결과 수
    
    Returns:
        검색 결과 리스트
    """
    for attempt in range(MAX_RETRIES):
        try:
            params = {
                "q": query,
                "api_key": serpapi_key,
                "engine": "google",
                "hl": "en",
                "gl": "us",
                "num": max_results
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            serp_results = []
            
            # Organic results
            if "organic_results" in results:
                for idx, item in enumerate(results["organic_results"][:max_results], 1):
                    serp_results.append({
                        "url": item.get("link", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "position": idx,
                        "source": extract_domain(item.get("link", ""))
                    })
            
            # 중복 제거
            serp_results = deduplicate_urls(serp_results)
            
            return serp_results
        
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF ** attempt + random.uniform(0, 1)
                logger.warning(f"Error fetching SERP results for '{query}' (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {wait_time:.2f}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch SERP results for '{query}' after {MAX_RETRIES} attempts: {e}")
                return []
    
    return []


def save_serp_results(
    cluster_id: int,
    query: str,
    results: List[Dict[str, Any]],
    run_id: int
) -> int:
    """
    SERP 결과를 DB에 저장
    
    Args:
        cluster_id: 클러스터 ID
        query: 검색 질문
        results: 검색 결과 리스트
        run_id: Pipeline run ID
    
    Returns:
        저장된 결과 수
    """
    if not results:
        return 0
    
    conn = None
    saved_count = 0
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for result in results:
                url = result.get("url", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                source = result.get("source", "")
                position = result.get("position", 0)
                
                if not url:
                    continue
                
                try:
                    cur.execute("""
                        INSERT INTO serp_results (
                            cluster_id, query, url, title, snippet, source, position
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (url, query) DO UPDATE SET
                            title = EXCLUDED.title,
                            snippet = EXCLUDED.snippet,
                            position = EXCLUDED.position,
                            fetched_at = CURRENT_TIMESTAMP
                    """, (cluster_id, query, url, title, snippet, source, position))
                    
                    if cur.rowcount > 0:
                        saved_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save SERP result '{url}': {e}")
                    continue
            
            conn.commit()
    
    finally:
        if conn:
            put_db_connection(conn)
    
    return saved_count


def collect_serp_results_for_cluster(
    cluster_id: int,
    queries: List[str],
    serpapi_key: str,
    run_id: int,
    dry_run: bool = False,
    max_results_per_query: int = 10
) -> Dict[str, Any]:
    """
    클러스터별 SERP 결과 수집
    
    Args:
        cluster_id: 클러스터 ID
        queries: 검색 질문 리스트
        serpapi_key: SerpAPI 키
        run_id: Pipeline run ID
        dry_run: Dry run mode
        max_results_per_query: 질문당 최대 결과 수
    
    Returns:
        Statistics dictionary
    """
    stats = {
        "queries_processed": 0,
        "queries_success": 0,
        "queries_failed": 0,
        "results_fetched": 0,
        "results_saved": 0,
        "errors": []
    }
    
    logger.info(f"Collecting SERP results for cluster {cluster_id} ({len(queries)} queries)")
    
    for query in queries:
        try:
            stats["queries_processed"] += 1
            
            if dry_run:
                logger.info(f"[DRY RUN] Would fetch SERP results for query: {query}")
                stats["queries_success"] += 1
                stats["results_fetched"] += max_results_per_query
                continue
            
            # SERP 결과 가져오기
            results = fetch_serp_results(query, serpapi_key, max_results=max_results_per_query)
            stats["results_fetched"] += len(results)
            
            if results:
                # DB에 저장
                saved = save_serp_results(cluster_id, query, results, run_id)
                stats["results_saved"] += saved
                stats["queries_success"] += 1
                
                logger.info(f"Query '{query}': {len(results)} results fetched, {saved} saved")
            else:
                stats["queries_failed"] += 1
                logger.warning(f"No results for query '{query}'")
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
        
        except Exception as e:
            stats["queries_failed"] += 1
            stats["errors"].append(f"{query}: {str(e)}")
            logger.error(f"Error processing query '{query}': {e}")
    
    return stats


def collect_serp_results_for_all_clusters(
    run_id: int,
    dry_run: bool = False,
    max_results_per_query: int = 10
) -> Dict[str, Any]:
    """
    모든 클러스터에 대해 SERP 결과 수집
    
    Args:
        run_id: Pipeline run ID
        dry_run: Dry run mode
        max_results_per_query: 질문당 최대 결과 수
    
    Returns:
        Statistics dictionary
    """
    serpapi_key = os.getenv("SERPAPI_KEY")
    
    if not serpapi_key and not dry_run:
        raise ValueError("SERPAPI_KEY not found in environment variables")
    
    logger.info(f"Starting SERP results collection (run_id={run_id})")
    
    stats = {
        "clusters_processed": 0,
        "total_queries_processed": 0,
        "total_queries_success": 0,
        "total_queries_failed": 0,
        "total_results_fetched": 0,
        "total_results_saved": 0,
        "clusters": []
    }
    
    # 1. 클러스터별 질문 로드
    conn = None
    cluster_queries = {}
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT csq.cluster_id, csq.query
                FROM cluster_serp_queries csq
                JOIN clusters c ON csq.cluster_id = c.cluster_id
                WHERE c.created_from_run_id = %s
                ORDER BY csq.cluster_id, csq.query
            """, (run_id,))
            
            for cluster_id, query in cur.fetchall():
                if cluster_id not in cluster_queries:
                    cluster_queries[cluster_id] = []
                cluster_queries[cluster_id].append(query)
    
    finally:
        if conn:
            put_db_connection(conn)
    
    if not cluster_queries:
        logger.warning(f"No queries found for run_id={run_id}")
        return stats
    
    logger.info(f"Found queries for {len(cluster_queries)} clusters")
    
    # 2. 각 클러스터별로 SERP 결과 수집
    for cluster_id, queries in cluster_queries.items():
        logger.info(f"Processing cluster {cluster_id} ({len(queries)} queries)")
        
        cluster_stats = collect_serp_results_for_cluster(
            cluster_id=cluster_id,
            queries=queries,
            serpapi_key=serpapi_key or "",
            run_id=run_id,
            dry_run=dry_run,
            max_results_per_query=max_results_per_query
        )
        
        stats["clusters_processed"] += 1
        stats["total_queries_processed"] += cluster_stats["queries_processed"]
        stats["total_queries_success"] += cluster_stats["queries_success"]
        stats["total_queries_failed"] += cluster_stats["queries_failed"]
        stats["total_results_fetched"] += cluster_stats["results_fetched"]
        stats["total_results_saved"] += cluster_stats["results_saved"]
        
        stats["clusters"].append({
            "cluster_id": cluster_id,
            "queries_processed": cluster_stats["queries_processed"],
            "results_saved": cluster_stats["results_saved"]
        })
    
    logger.info(f"SERP results collection completed:")
    logger.info(f"  Clusters processed: {stats['clusters_processed']}")
    logger.info(f"  Queries processed: {stats['total_queries_processed']}")
    logger.info(f"  Queries success: {stats['total_queries_success']}")
    logger.info(f"  Queries failed: {stats['total_queries_failed']}")
    logger.info(f"  Results fetched: {stats['total_results_fetched']}")
    logger.info(f"  Results saved: {stats['total_results_saved']}")
    
    return stats
