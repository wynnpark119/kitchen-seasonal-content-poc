#!/usr/bin/env python3
"""
SERP 수집 스크립트
4개 topic_category별 SERP 쿼리 리스트로 SERP API 요청을 보내고,
결과를 DB에 topic_category 기준으로 구분 저장
"""
import os
import sys
import time
import hashlib
import re
import json
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from serpapi import GoogleSearch
from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.logging import setup_logger

logger = setup_logger("run_serp_collection")

# ============================================================================
# 쿼리 리스트 정의 (4개 topic_category별 25개씩)
# ============================================================================

SERP_QUERIES = {
    "SPRING_RECIPES": [
        "What are some easy spring dinner ideas?",
        "How do I cook spring vegetables?",
        "What are the best spring recipes?",
        "How to make light spring meals?",
        "What should I cook in spring?",
        "What are healthy spring dinner options?",
        "How to prepare spring vegetables?",
        "What are quick spring meal ideas?",
        "How do you cook spring produce?",
        "What are simple spring recipes?",
        "How to make spring comfort food?",
        "What are the best spring weeknight meals?",
        "How do I meal prep for spring?",
        "What are spring cooking ideas?",
        "How to cook spring vegetables properly?",
        "What are some spring dinner recipes?",
        "How do you use spring vegetables?",
        "What are the best ways to cook spring produce?",
        "How to make spring meals healthy?",
        "What are spring meal prep ideas?",
        "How do I prepare spring vegetables for cooking?",
        "What are some spring comfort food recipes?",
        "How to cook spring vegetables quickly?",
        "What are the best spring dinner ideas?",
        "How do you make spring meals taste good?"
    ],
    "REFRIGERATOR_ORGANIZATION": [
        "How do I organize my refrigerator?",
        "What are the best refrigerator organization tips?",
        "How to organize fridge efficiently?",
        "What are refrigerator storage ideas?",
        "How do you organize a refrigerator?",
        "What are the best fridge organization methods?",
        "How to organize refrigerator drawers?",
        "What are refrigerator organization hacks?",
        "How do I keep my fridge organized?",
        "What are the best ways to organize a refrigerator?",
        "How to organize refrigerator shelves?",
        "What are refrigerator organization systems?",
        "How do you organize refrigerator door?",
        "What are the best refrigerator organization containers?",
        "How to organize small refrigerator?",
        "What are refrigerator organization tips for families?",
        "How do I organize my refrigerator better?",
        "What are refrigerator organization before and after ideas?",
        "How to organize refrigerator for meal prep?",
        "What are the best refrigerator organization bins?",
        "How do you organize refrigerator storage?",
        "What are refrigerator organization labels?",
        "How to organize refrigerator routine?",
        "What are the best refrigerator organization methods?",
        "How do I maintain refrigerator organization?"
    ],
    "VEGETABLE_PREP_HANDLING": [
        "How do I prep vegetables?",
        "What are the best vegetable prep tips?",
        "How to prep vegetables for meal prep?",
        "What are vegetable storage tips?",
        "How do you wash vegetables properly?",
        "What are the best ways to prep vegetables?",
        "How to store vegetables?",
        "What are vegetable prep methods?",
        "How do I clean vegetables?",
        "What are vegetable handling tips?",
        "How to prep vegetables ahead of time?",
        "What are vegetable storage containers?",
        "How do you store cut vegetables?",
        "What are vegetable prep ideas?",
        "How to wash vegetables correctly?",
        "What are vegetable prep containers?",
        "How do I prep vegetables for cooking?",
        "What are vegetable storage methods?",
        "How to prep vegetables quickly?",
        "What are vegetable prep tips?",
        "How do you prep vegetables for meal prep?",
        "What are vegetable washing methods?",
        "How to store vegetables in refrigerator?",
        "What are vegetable prep routines?",
        "How do I handle vegetables properly?"
    ],
    "SPRING_KITCHEN_STYLING": [
        "How do I decorate my kitchen for spring?",
        "What are spring kitchen decor ideas?",
        "How to style kitchen for spring?",
        "What are spring kitchen decoration tips?",
        "How do you decorate kitchen for spring?",
        "What are the best spring kitchen ideas?",
        "How to refresh kitchen for spring?",
        "What are spring kitchen styling ideas?",
        "How do I style my kitchen for spring?",
        "What are spring kitchen decor tips?",
        "How to decorate kitchen with spring colors?",
        "What are spring kitchen accessories?",
        "How do you refresh kitchen decor for spring?",
        "What are spring kitchen centerpiece ideas?",
        "How to style kitchen table for spring?",
        "What are spring kitchen window decor ideas?",
        "How do I make my kitchen feel like spring?",
        "What are spring kitchen counter decor ideas?",
        "How to decorate kitchen walls for spring?",
        "What are spring kitchen lighting ideas?",
        "How do you add spring touches to kitchen?",
        "What are spring kitchen plants?",
        "How to style kitchen for spring season?",
        "What are spring kitchen rug ideas?",
        "How do I create spring kitchen atmosphere?"
    ]
}

# ============================================================================
# 환경변수 확인
# ============================================================================

def check_and_run_migration():
    """마이그레이션 확인 및 실행"""
    conn = None
    max_retries = 3
    for retry in range(max_retries):
        try:
            conn = get_db_connection()
            break
        except Exception as e:
            if retry < max_retries - 1:
                wait_time = 2 ** retry
                logger.warning(f"DB 연결 실패 (시도 {retry + 1}/{max_retries}), {wait_time}초 후 재시도: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"DB 연결 실패 (최대 재시도 횟수 초과): {e}")
                logger.error("DATABASE_URL을 확인해주세요. Railway 대시보드에서 DATABASE_URL을 확인하거나")
                logger.error("환경변수로 직접 설정해주세요: export DATABASE_URL='postgresql://...'")
                raise
    
    try:
        with conn.cursor() as cur:
            # 먼저 serp_results 테이블 존재 여부 확인
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'serp_results'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                logger.info("serp_results 테이블이 없습니다. 기본 테이블 생성 중...")
                # 기본 테이블 생성 (cluster_id는 NULL 허용, topic_category 기반 사용)
                cur.execute("""
                    CREATE TABLE serp_results (
                        id SERIAL PRIMARY KEY,
                        cluster_id INTEGER,
                        topic_category VARCHAR(50),
                        query TEXT NOT NULL,
                        url TEXT NOT NULL,
                        title TEXT,
                        snippet TEXT,
                        source VARCHAR(255),
                        position INTEGER,
                        engine VARCHAR(50) DEFAULT 'google',
                        dedup_hash TEXT,
                        fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("  → serp_results 테이블 생성 완료")
                conn.commit()
            
            # topic_category 컬럼 존재 여부 확인
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'serp_results' 
                AND column_name = 'topic_category'
            """)
            
            if not cur.fetchone():
                logger.info("마이그레이션 실행 중...")
                
                # 컬럼 추가 (IF NOT EXISTS는 PostgreSQL에서 직접 지원하지 않으므로 try-except 사용)
                try:
                    cur.execute("ALTER TABLE serp_results ADD COLUMN topic_category VARCHAR(50)")
                    logger.info("  → topic_category 컬럼 추가 완료")
                except Exception as e:
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        logger.warning(f"  → topic_category 컬럼 추가 중 경고: {e}")
                
                try:
                    cur.execute("ALTER TABLE serp_results ADD COLUMN engine VARCHAR(50) DEFAULT 'google'")
                    logger.info("  → engine 컬럼 추가 완료")
                except Exception as e:
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        logger.warning(f"  → engine 컬럼 추가 중 경고: {e}")
                
                try:
                    cur.execute("ALTER TABLE serp_results ADD COLUMN dedup_hash TEXT")
                    logger.info("  → dedup_hash 컬럼 추가 완료")
                except Exception as e:
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        logger.warning(f"  → dedup_hash 컬럼 추가 중 경고: {e}")
                
                # 인덱스 추가
                try:
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_serp_results_topic_category ON serp_results(topic_category)")
                    logger.info("  → topic_category 인덱스 추가 완료")
                except Exception as e:
                    logger.warning(f"  → 인덱스 추가 중 경고: {e}")
                
                try:
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_serp_results_dedup_hash ON serp_results(dedup_hash)")
                    logger.info("  → dedup_hash 인덱스 추가 완료")
                except Exception as e:
                    logger.warning(f"  → 인덱스 추가 중 경고: {e}")
                
                # 기존 UNIQUE 제약조건 제거 시도
                try:
                    cur.execute("ALTER TABLE serp_results DROP CONSTRAINT IF EXISTS uk_serp_result_url_query")
                    logger.info("  → 기존 UNIQUE 제약조건 제거 완료")
                except Exception as e:
                    logger.debug(f"  → 제약조건 제거 중 (무시 가능): {e}")
                
                # 새로운 UNIQUE 제약조건 추가 시도
                try:
                    cur.execute("""
                        ALTER TABLE serp_results 
                        ADD CONSTRAINT uk_serp_result_topic_query_url 
                        UNIQUE (topic_category, query, url)
                    """)
                    logger.info("  → 새로운 UNIQUE 제약조건 추가 완료")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"  → UNIQUE 제약조건 추가 중 경고 (기존 제약조건과 충돌 가능): {e}")
                
                conn.commit()
                logger.info("마이그레이션 완료")
            else:
                logger.info("마이그레이션 확인 완료 (topic_category 컬럼 존재)")
    
    except Exception as e:
        logger.error(f"마이그레이션 확인 중 오류: {e}")
        raise
    finally:
        if conn:
            put_db_connection(conn)

def check_environment_variables():
    """필수 환경변수 확인"""
    required_vars = {
        "SERP_API_KEY": os.getenv("SERP_API_KEY"),
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        logger.error("=" * 80)
        logger.error("필수 환경변수가 설정되지 않았습니다:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("=" * 80)
        sys.exit(1)
    
    # 선택적 환경변수
    optional_vars = {
        "SERP_ENGINE": os.getenv("SERP_ENGINE", "google"),
        "SERP_LOCATION": os.getenv("SERP_LOCATION", "us"),
        "SERP_GL": os.getenv("SERP_GL", "us"),
        "SERP_HL": os.getenv("SERP_HL", "en"),
        "SERP_NUM_RESULTS": int(os.getenv("SERP_NUM_RESULTS", "10")),
        "SERP_TIMEOUT_SEC": int(os.getenv("SERP_TIMEOUT_SEC", "30")),
        "SERP_CONCURRENCY": int(os.getenv("SERP_CONCURRENCY", "2")),
    }
    
    logger.info("환경변수 확인 완료:")
    logger.info(f"  SERP_API_KEY: {'*' * 20} (설정됨)")
    for var, value in optional_vars.items():
        logger.info(f"  {var}: {value}")
    
    return {
        "api_key": required_vars["SERP_API_KEY"],
        **optional_vars
    }

# ============================================================================
# 유틸리티 함수
# ============================================================================

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
    """URL 정규화 (쿼리 파라미터 제거 등)"""
    try:
        parsed = urlparse(url)
        # scheme + netloc + path만 사용 (쿼리, 프래그먼트 제거)
        canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return canonical.rstrip('/')
    except:
        return url

# ============================================================================
# SERP API 호출
# ============================================================================

def fetch_serp_results(
    query: str,
    config: Dict[str, Any],
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    """
    SERP API로 검색 결과 가져오기
    
    Args:
        query: 검색 질문
        config: 환경변수 설정
        max_retries: 최대 재시도 횟수
    
    Returns:
        검색 결과 리스트
    """
    for attempt in range(max_retries):
        try:
            params = {
                "q": query,
                "api_key": config["api_key"],
                "engine": config["SERP_ENGINE"],
                "hl": config["SERP_HL"],
                "gl": config["SERP_GL"],
                "num": config["SERP_NUM_RESULTS"]
            }
            
            # location 파라미터는 SerpAPI에서 특정 형식만 지원하므로 제거
            # 필요시 "United States" 같은 전체 이름 사용
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            serp_results = []
            
            # 에러 확인
            if "error" in results:
                error_msg = results.get("error", "Unknown error")
                logger.error(f"SerpAPI 에러: {error_msg}")
                return []
            
            # Organic results 파싱
            if "organic_results" in results:
                for idx, item in enumerate(results["organic_results"][:config["SERP_NUM_RESULTS"]], 1):
                    url = item.get("link", "")
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    
                    if not url:
                        continue
                    
                    canonical_url = canonicalize_url(url)
                    dedup_hash = generate_dedup_hash(canonical_url, title)
                    
                    serp_results.append({
                        "url": canonical_url,
                        "title": title,
                        "snippet": snippet,
                        "position": idx,
                        "source": extract_domain(url),
                        "dedup_hash": dedup_hash
                    })
            else:
                logger.debug(f"organic_results가 응답에 없음. 응답 키: {list(results.keys())[:10]}")
            
            return serp_results
        
        except Exception as e:
            error_str = str(e).lower()
            
            # 400류 에러는 재시도하지 않음
            if "400" in error_str or "bad request" in error_str or "invalid" in error_str:
                logger.error(f"Query '{query}': 입력 오류 (재시도 안 함): {e}")
                return []
            
            # 429/5xx/timeout만 재시도
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + (attempt * 0.5)  # exponential backoff
                logger.warning(
                    f"Query '{query}' 실패 (시도 {attempt + 1}/{max_retries}), "
                    f"{wait_time:.1f}초 후 재시도: {e}"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Query '{query}' 실패 (최대 재시도 횟수 초과): {e}")
                return []
    
    return []

# ============================================================================
# DB 저장
# ============================================================================

def save_serp_results_to_db(
    topic_category: str,
    query: str,
    results: List[Dict[str, Any]],
    config: Dict[str, Any]
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
                
                try:
                    cur.execute("""
                        INSERT INTO serp_results (
                            topic_category, query, url, title, snippet,
                            source, position, engine, dedup_hash, fetched_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (topic_category, query, url) DO UPDATE SET
                            title = EXCLUDED.title,
                            snippet = EXCLUDED.snippet,
                            position = EXCLUDED.position,
                            source = EXCLUDED.source,
                            dedup_hash = EXCLUDED.dedup_hash,
                            fetched_at = CURRENT_TIMESTAMP
                        RETURNING (xmax = 0) AS inserted
                    """, (
                        topic_category,
                        query,
                        url,
                        title,
                        snippet,
                        source,
                        position,
                        config["SERP_ENGINE"],
                        dedup_hash,
                        datetime.utcnow()
                    ))
                    
                    row = cur.fetchone()
                    if row and row[0]:  # inserted = True
                        stats["saved"] += 1
                    else:
                        stats["skipped"] += 1
                        
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

# ============================================================================
# 메인 수집 로직
# ============================================================================

def save_results_to_json(stats: Dict[str, Any], output_file: str = "serp_collection_results.json"):
    """결과를 JSON 파일로 저장"""
    output_path = project_root / "data" / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # JSON 직렬화 가능한 형태로 변환
    json_stats = {
        "total_topics": stats["total_topics"],
        "total_queries": stats["total_queries"],
        "total_results_saved": stats["total_results_saved"],
        "total_results_skipped": stats["total_results_skipped"],
        "total_queries_failed": stats["total_queries_failed"],
        "topic_stats": {},
        "errors": stats["errors"],
        "collected_at": datetime.utcnow().isoformat(),
        "raw_results": stats.get("raw_results", {})  # 원시 결과 데이터 포함
    }
    
    # topic_stats 변환 (set을 list로)
    for topic, topic_stat in stats["topic_stats"].items():
        json_stats["topic_stats"][topic] = {
            "queries_run": topic_stat["queries_run"],
            "queries_success": topic_stat["queries_success"],
            "queries_failed": topic_stat["queries_failed"],
            "results_saved": topic_stat["results_saved"],
            "results_skipped": topic_stat["results_skipped"],
            "unique_urls": topic_stat["unique_urls"],
            "last_fetched_at": topic_stat["last_fetched_at"],
            "errors": topic_stat["errors"]
        }
    
    # raw_results 포함 (이미 변환된 형태)
    if "raw_results" in stats:
        json_stats["raw_results"] = stats["raw_results"]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_stats, f, indent=2, ensure_ascii=False)
    
    logger.info(f"결과를 JSON 파일로 저장: {output_path}")
    return str(output_path)

def collect_serp_by_topic_category(config: Dict[str, Any], save_json: bool = True) -> Dict[str, Any]:
    """
    topic_category별 SERP 수집
    
    Returns:
        통계 딕셔너리
    """
    overall_stats = {
        "total_topics": len(SERP_QUERIES),
        "total_queries": sum(len(queries) for queries in SERP_QUERIES.values()),
        "total_results_saved": 0,
        "total_results_skipped": 0,
        "total_queries_failed": 0,
        "topic_stats": {},
        "errors": [],
        "raw_results": {}  # JSON 저장용 원시 데이터
    }
    
    concurrency = config["SERP_CONCURRENCY"]
    rate_limit_delay = 1.0 / concurrency  # 동시성에 따른 딜레이 조정
    
    logger.info("=" * 80)
    logger.info("SERP 수집 시작")
    logger.info(f"  총 topic_category 수: {overall_stats['total_topics']}")
    logger.info(f"  총 query 수: {overall_stats['total_queries']}")
    logger.info(f"  동시성: {concurrency}")
    logger.info("=" * 80)
    
    for topic_category, queries in SERP_QUERIES.items():
        logger.info("")
        logger.info(f"[{topic_category}] 시작 ({len(queries)}개 쿼리)")
        logger.info("-" * 80)
        
        topic_stats = {
            "queries_run": 0,
            "queries_success": 0,
            "queries_failed": 0,
            "results_saved": 0,
            "results_skipped": 0,
            "unique_urls": set(),
            "last_fetched_at": None,
            "errors": [],
            "query_results": []  # JSON 저장용 쿼리별 결과
        }
        
        for idx, query in enumerate(queries, 1):
            try:
                topic_stats["queries_run"] += 1
                
                logger.info(f"  [{idx}/{len(queries)}] Query: {query}")
                
                # SERP API 호출
                try:
                    results = fetch_serp_results(query, config)
                except Exception as e:
                    topic_stats["queries_failed"] += 1
                    overall_stats["total_queries_failed"] += 1
                    error_msg = f"{query}: {str(e)}"
                    topic_stats["errors"].append(error_msg)
                    overall_stats["errors"].append(f"[{topic_category}] {error_msg}")
                    logger.error(f"    → SERP API 호출 실패: {e}")
                    continue
                
                if not results:
                    topic_stats["queries_failed"] += 1
                    overall_stats["total_queries_failed"] += 1
                    logger.warning(f"    → 결과 없음 (응답은 받았지만 organic_results가 비어있음)")
                    continue
                
                # DB 저장 (SAVE_TO_DB가 true일 때만)
                save_to_db = os.getenv("SAVE_TO_DB", "true").lower() == "true"
                if save_to_db:
                    save_stats = save_serp_results_to_db(topic_category, query, results, config)
                else:
                    # JSON만 저장하는 경우 가짜 통계 생성
                    save_stats = {"saved": len(results), "skipped": 0}
                
                topic_stats["results_saved"] += save_stats["saved"]
                topic_stats["results_skipped"] += save_stats["skipped"]
                topic_stats["unique_urls"].update(r["url"] for r in results)
                
                if save_stats["saved"] > 0:
                    topic_stats["queries_success"] += 1
                    logger.info(
                        f"    → 성공: {len(results)}개 결과, "
                        f"{save_stats['saved']}개 저장, "
                        f"{save_stats['skipped']}개 스킵"
                    )
                else:
                    logger.warning(f"    → 모든 결과가 스킵됨 (중복)")
                
                # JSON 저장용 데이터 수집
                if save_json:
                    topic_stats["query_results"].append({
                        "query": query,
                        "results_count": len(results),
                        "saved": save_stats["saved"],
                        "skipped": save_stats["skipped"],
                        "results": results
                    })
                
                overall_stats["total_results_saved"] += save_stats["saved"]
                overall_stats["total_results_skipped"] += save_stats["skipped"]
                
                # Rate limiting
                if idx < len(queries):  # 마지막 쿼리가 아니면
                    time.sleep(rate_limit_delay)
            
            except Exception as e:
                topic_stats["queries_failed"] += 1
                overall_stats["total_queries_failed"] += 1
                error_msg = f"{query}: {str(e)}"
                topic_stats["errors"].append(error_msg)
                overall_stats["errors"].append(f"[{topic_category}] {error_msg}")
                logger.error(f"    → 오류: {e}")
        
        # topic_stats 정리
        topic_stats["unique_urls"] = len(topic_stats["unique_urls"])
        topic_stats["last_fetched_at"] = datetime.utcnow().isoformat()
        
        # topic_stats 정리 (set을 int로 변환)
        if isinstance(topic_stats["unique_urls"], set):
            topic_stats["unique_urls"] = len(topic_stats["unique_urls"])
        overall_stats["topic_stats"][topic_category] = topic_stats
        
        # JSON 저장용 데이터 수집
        if save_json:
            overall_stats["raw_results"][topic_category] = topic_stats["query_results"]
        
        logger.info("")
        logger.info(f"[{topic_category}] 완료:")
        logger.info(f"  쿼리 실행: {topic_stats['queries_run']}")
        logger.info(f"  쿼리 성공: {topic_stats['queries_success']}")
        logger.info(f"  쿼리 실패: {topic_stats['queries_failed']}")
        logger.info(f"  결과 저장: {topic_stats['results_saved']}")
        logger.info(f"  결과 스킵: {topic_stats['results_skipped']}")
        logger.info(f"  고유 URL: {topic_stats['unique_urls']}")
    
    # JSON 파일로 저장
    if save_json:
        json_file = save_results_to_json(overall_stats)
        logger.info(f"전체 결과를 JSON 파일로 저장 완료: {json_file}")
    
    return overall_stats

# ============================================================================
# 결과 출력
# ============================================================================

def print_results(stats: Dict[str, Any]):
    """결과를 표 형태로 출력"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("수집 결과 요약")
    logger.info("=" * 80)
    
    # A) 전체 통계
    logger.info("")
    logger.info("A) 전체 통계")
    logger.info("-" * 80)
    logger.info(f"  총 topic_category 수: {stats['total_topics']}")
    logger.info(f"  총 query 수: {stats['total_queries']}")
    logger.info(f"  총 SERP row 저장 수: {stats['total_results_saved']}")
    logger.info(f"  중복으로 스킵된 row 수: {stats['total_results_skipped']}")
    logger.info(f"  실패 query 수: {stats['total_queries_failed']}")
    
    # 에러 요약 Top 5
    if stats["errors"]:
        logger.info("")
        logger.info("  실패 query 에러 요약 (Top 5):")
        for i, error in enumerate(stats["errors"][:5], 1):
            logger.info(f"    {i}. {error}")
    
    # B) topic_category별 통계 테이블
    logger.info("")
    logger.info("B) topic_category별 통계")
    logger.info("-" * 80)
    logger.info(f"{'topic_category':<30} {'queries_run':<12} {'results_saved':<14} {'unique_urls':<12} {'last_fetched_at':<20}")
    logger.info("-" * 80)
    
    for topic_category, topic_stats in stats["topic_stats"].items():
        logger.info(
            f"{topic_category:<30} "
            f"{topic_stats['queries_run']:<12} "
            f"{topic_stats['results_saved']:<14} "
            f"{topic_stats['unique_urls']:<12} "
            f"{topic_stats['last_fetched_at'][:19] if topic_stats['last_fetched_at'] else 'N/A':<20}"
        )
    
    # C) 샘플 출력
    logger.info("")
    logger.info("C) 샘플 출력 (각 topic_category별 5개 row)")
    logger.info("-" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for topic_category in SERP_QUERIES.keys():
                logger.info("")
                logger.info(f"[{topic_category}] 샘플:")
                logger.info("-" * 80)
                
                cur.execute("""
                    SELECT query, title, url, snippet
                    FROM serp_results
                    WHERE topic_category = %s
                    ORDER BY fetched_at DESC
                    LIMIT 5
                """, (topic_category,))
                
                rows = cur.fetchall()
                if not rows:
                    logger.info("  (데이터 없음)")
                    continue
                
                for i, (query, title, url, snippet) in enumerate(rows, 1):
                    snippet_preview = (snippet or "")[:150] + "..." if snippet and len(snippet) > 150 else (snippet or "")
                    logger.info(f"  {i}. Query: {query}")
                    logger.info(f"     Title: {title}")
                    logger.info(f"     URL: {url}")
                    logger.info(f"     Snippet: {snippet_preview}")
                    logger.info("")
    
    finally:
        if conn:
            put_db_connection(conn)
    
    # D) 최종 판정
    logger.info("")
    logger.info("=" * 80)
    logger.info("최종 판정")
    logger.info("=" * 80)
    
    # DB 적재 확인
    db_success = stats["total_results_saved"] > 0
    logger.info(f"  DB 적재: {'SUCCESS' if db_success else 'FAIL'}")
    
    # 주제 구분 저장 확인
    topic_separation_pass = all(
        topic_stats["results_saved"] > 0 
        for topic_stats in stats["topic_stats"].values()
    )
    logger.info(f"  주제 구분 저장: {'PASS' if topic_separation_pass else 'FAIL'}")
    
    # 다음 단계 진행 가능 여부
    can_proceed = db_success and topic_separation_pass and stats["total_queries_failed"] == 0
    logger.info(f"  다음 단계 진행 가능: {'YES' if can_proceed else 'NO'}")
    
    if not can_proceed:
        logger.info("")
        logger.info("실패 원인:")
        if not db_success:
            logger.info("  - DB에 데이터가 저장되지 않음")
        if not topic_separation_pass:
            failed_topics = [
                topic for topic, topic_stats in stats["topic_stats"].items()
                if topic_stats["results_saved"] == 0
            ]
            logger.info(f"  - 다음 topic_category에 데이터가 없음: {', '.join(failed_topics)}")
        if stats["total_queries_failed"] > 0:
            logger.info(f"  - {stats['total_queries_failed']}개 쿼리 실패")
    
    logger.info("=" * 80)

# ============================================================================
# 메인 실행
# ============================================================================

def main():
    """메인 실행 함수"""
    try:
        # 환경변수 확인
        config = check_environment_variables()
        
        # 마이그레이션 확인 및 실행 (DB 저장 모드일 때만)
        save_to_db = os.getenv("SAVE_TO_DB", "true").lower() == "true"
        if save_to_db:
            check_and_run_migration()
        else:
            logger.info("DB 저장 모드 비활성화 (SAVE_TO_DB=false), JSON만 저장합니다")
        
        # SERP 수집 실행
        stats = collect_serp_by_topic_category(config, save_json=True)
        
        # 결과 출력
        print_results(stats)
        
        # 최종 판정
        success = (
            stats["total_results_saved"] > 0 and
            all(topic_stats["results_saved"] > 0 for topic_stats in stats["topic_stats"].values())
        )
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단됨")
        sys.exit(130)
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
