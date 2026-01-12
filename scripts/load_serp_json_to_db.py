#!/usr/bin/env python3
"""
JSON 파일에서 SERP 결과를 DB에 적재하는 스크립트
"""
import os
import sys
import json
import hashlib
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.logging import setup_logger

logger = setup_logger("load_serp_json_to_db")

def extract_domain(url: str) -> str:
    """URL에서 도메인 추출"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    except:
        return ""

def generate_dedup_hash(url: str, title: str) -> str:
    """URL과 title 기반 중복 방지 해시 생성"""
    combined = f"{url}|{title}".lower().strip()
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def canonicalize_url(url: str) -> str:
    """URL 정규화"""
    try:
        parsed = urlparse(url)
        canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return canonical.rstrip('/')
    except:
        return url

def load_json_file(json_path: str) -> Dict[str, Any]:
    """JSON 파일 로드"""
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"JSON 파일 로드 완료: {json_path}")
    return data

def save_results_to_db(
    topic_category: str,
    query: str,
    results: List[Dict[str, Any]],
    engine: str = "google"
) -> Dict[str, int]:
    """
    SERP 결과를 DB에 저장
    
    Returns:
        {"saved": 저장된 수, "skipped": 스킵된 수}
    """
    if not results:
        return {"saved": 0, "skipped": 0}
    
    conn = None
    stats = {"saved": 0, "skipped": 0}
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for result in results:
                url = result.get("url", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                source = result.get("source", "")
                position = result.get("position", 0)
                dedup_hash = result.get("dedup_hash", "")
                
                if not url:
                    continue
                
                # dedup_hash가 없으면 생성
                if not dedup_hash:
                    canonical_url = canonicalize_url(url)
                    dedup_hash = generate_dedup_hash(canonical_url, title)
                    url = canonical_url
                
                # source가 없으면 추출
                if not source:
                    source = extract_domain(url)
                
                try:
                    # 먼저 존재 여부 확인
                    cur.execute("""
                        SELECT id FROM serp_results 
                        WHERE topic_category = %s AND query = %s AND url = %s
                    """, (topic_category, query, url))
                    
                    existing = cur.fetchone()
                    
                    if existing:
                        # 업데이트
                        cur.execute("""
                            UPDATE serp_results SET
                                title = %s,
                                snippet = %s,
                                position = %s,
                                source = %s,
                                dedup_hash = %s,
                                fetched_at = CURRENT_TIMESTAMP
                            WHERE topic_category = %s AND query = %s AND url = %s
                        """, (
                            title, snippet, position, source, dedup_hash,
                            topic_category, query, url
                        ))
                        stats["skipped"] += 1
                    else:
                        # 삽입
                        cur.execute("""
                            INSERT INTO serp_results (
                                topic_category, query, url, title, snippet,
                                source, position, engine, dedup_hash, fetched_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                        topic_category,
                        query,
                        url,
                        title,
                        snippet,
                        source,
                        position,
                        engine,
                        dedup_hash,
                            datetime.utcnow()
                        ))
                        stats["saved"] += 1
                        
                except Exception as e:
                    logger.warning(f"결과 저장 실패 (url: {url[:50]}...): {e}")
                    stats["skipped"] += 1
                    continue
            
            conn.commit()
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"DB 저장 중 오류: {e}")
        raise
    
    finally:
        if conn:
            put_db_connection(conn)
    
    return stats

def load_serp_json_to_db(json_path: str = "data/serp_collection_results.json") -> Dict[str, Any]:
    """
    JSON 파일에서 SERP 결과를 DB에 적재
    
    Args:
        json_path: JSON 파일 경로
    
    Returns:
        통계 딕셔너리
    """
    # JSON 파일 로드
    data = load_json_file(json_path)
    
    # raw_results 확인
    if "raw_results" not in data or not data["raw_results"]:
        logger.error("JSON 파일에 raw_results가 없습니다. 수집 스크립트를 다시 실행하거나")
        logger.error("JSON 파일 구조를 확인해주세요.")
        raise ValueError("raw_results가 JSON 파일에 없습니다")
    
    overall_stats = {
        "total_topics": 0,
        "total_queries": 0,
        "total_results_saved": 0,
        "total_results_skipped": 0,
        "topic_stats": {}
    }
    
    logger.info("=" * 80)
    logger.info("JSON에서 DB로 데이터 적재 시작")
    logger.info("=" * 80)
    
    # 각 topic_category별로 처리
    for topic_category, query_results in data["raw_results"].items():
        logger.info("")
        logger.info(f"[{topic_category}] 시작 ({len(query_results)}개 쿼리)")
        logger.info("-" * 80)
        
        topic_stats = {
            "queries_processed": 0,
            "results_saved": 0,
            "results_skipped": 0
        }
        
        for query_data in query_results:
            query = query_data.get("query", "")
            results = query_data.get("results", [])
            
            if not query or not results:
                continue
            
            topic_stats["queries_processed"] += 1
            
            logger.info(f"  [{topic_stats['queries_processed']}/{len(query_results)}] Query: {query}")
            
            # DB 저장
            save_stats = save_results_to_db(topic_category, query, results)
            
            topic_stats["results_saved"] += save_stats["saved"]
            topic_stats["results_skipped"] += save_stats["skipped"]
            
            overall_stats["total_results_saved"] += save_stats["saved"]
            overall_stats["total_results_skipped"] += save_stats["skipped"]
            
            logger.info(
                f"    → {len(results)}개 결과, "
                f"{save_stats['saved']}개 저장, "
                f"{save_stats['skipped']}개 스킵"
            )
        
        overall_stats["total_topics"] += 1
        overall_stats["total_queries"] += topic_stats["queries_processed"]
        overall_stats["topic_stats"][topic_category] = topic_stats
        
        logger.info("")
        logger.info(f"[{topic_category}] 완료:")
        logger.info(f"  쿼리 처리: {topic_stats['queries_processed']}")
        logger.info(f"  결과 저장: {topic_stats['results_saved']}")
        logger.info(f"  결과 스킵: {topic_stats['results_skipped']}")
    
    return overall_stats

def print_results(stats: Dict[str, Any]):
    """결과 출력"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("DB 적재 결과 요약")
    logger.info("=" * 80)
    
    logger.info(f"  총 topic_category 수: {stats['total_topics']}")
    logger.info(f"  총 query 수: {stats['total_queries']}")
    logger.info(f"  총 결과 저장: {stats['total_results_saved']}")
    logger.info(f"  총 결과 스킵: {stats['total_results_skipped']}")
    
    logger.info("")
    logger.info("topic_category별 통계:")
    logger.info("-" * 80)
    logger.info(f"{'topic_category':<30} {'queries':<12} {'saved':<12} {'skipped':<12}")
    logger.info("-" * 80)
    
    for topic_category, topic_stats in stats["topic_stats"].items():
        logger.info(
            f"{topic_category:<30} "
            f"{topic_stats['queries_processed']:<12} "
            f"{topic_stats['results_saved']:<12} "
            f"{topic_stats['results_skipped']:<12}"
        )
    
    logger.info("=" * 80)

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JSON 파일에서 SERP 결과를 DB에 적재")
    parser.add_argument(
        "--json-file",
        default="data/serp_collection_results.json",
        help="JSON 파일 경로 (기본: data/serp_collection_results.json)"
    )
    
    args = parser.parse_args()
    
    try:
        # DB 적재 실행
        stats = load_serp_json_to_db(args.json_file)
        
        # 결과 출력
        print_results(stats)
        
        # 최종 판정
        success = stats["total_results_saved"] > 0
        logger.info("")
        logger.info(f"DB 적재: {'SUCCESS' if success else 'FAIL'}")
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단됨")
        sys.exit(130)
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
