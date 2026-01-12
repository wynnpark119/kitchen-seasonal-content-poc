# DB 커넥션 풀 고갈 문제 상세 분석 및 수정

## [A] 원인 후보 Top 3

### 1. 함수 시작 시 커넥션 획득 후 장기 점유 (최우선)
**위치**: `worker/pipeline/embedding.py:111`
```python
def generate_embeddings(...):
    conn = get_db_connection()  # ❌ 함수 시작 시 획득
    try:
        with conn.cursor() as cur:
            # ... 전체 로직 (수백~수천 개 포스트 처리)
            # API 호출 중에도 커넥션 점유됨 (라인 200)
            embeddings = generate_embeddings_batch(batch, client)  # 수 초~수십 초 대기
```
**근거**: 
- 커넥션이 함수 전체에 걸쳐 점유됨
- API 호출 중(수 초~수십 초)에도 커넥션이 반납되지 않음
- 배치 처리 중 여러 배치가 동시에 실행되면 풀 고갈

### 2. 중복 체크를 위한 개별 쿼리 실행
**위치**: `worker/pipeline/embedding.py:176-184`
```python
for idx, (post_id, title, body) in enumerate(all_posts, 1):
    # ... 텍스트 처리 ...
    cur.execute("""
        SELECT 1 FROM embeddings WHERE text_hash = %s LIMIT 1
    """, (text_hash,))  # ❌ 각 포스트마다 개별 쿼리
```
**근거**:
- 각 포스트마다 개별 SELECT 쿼리 실행
- 커넥션이 오래 점유됨
- 배치로 처리 가능한데 개별 처리

### 3. DB write 동시성 제한 없음
**위치**: `worker/pipeline/embedding.py:209`
```python
upsert_embeddings_batch(embeddings_data, run_id)  # 동시성 제한 없음
```
**근거**:
- 여러 배치가 동시에 실행될 수 있음
- 각 배치가 각각 커넥션을 획득
- 동시 실행 시 풀 고갈 가능

## [B] 수정안

### 변경 파일 리스트
1. `worker/pipeline/db.py` - 풀 설정, fallback 정책 변경
2. `worker/pipeline/embedding.py` - 커넥션 점유 제거, 동시성 제한, 배치 처리
3. `worker/pipeline/config.py` - 환경 변수 추가

### 핵심 Diff

#### 1. 커넥션 점유 제거 (`embedding.py`)
```python
# Before: 함수 시작 시 커넥션 획득
def generate_embeddings(...):
    conn = get_db_connection()  # ❌
    try:
        with conn.cursor() as cur:
            # ... 전체 로직 ...
            embeddings = generate_embeddings_batch(...)  # API 호출 중 점유

# After: 필요한 시점에만 커넥션 획득
def generate_embeddings(...):
    # 1. 포스트 목록 조회 (짧은 트랜잭션)
    with get_db_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
            all_posts = cur.fetchall()
    
    # 2. 중복 체크 배치 처리 (짧은 트랜잭션)
    existing_hashes = check_existing_hashes_batch(text_hashes)
    
    # 3. API 호출 (커넥션 없음)
    embeddings = generate_embeddings_batch(batch, client)
    
    # 4. DB 저장 (짧은 트랜잭션, 동시성 제한)
    with db_write_semaphore:  # 동시성 제한
        upsert_embeddings_batch(embeddings_data, run_id)
```

#### 2. DB write 동시성 제한 (`embedding.py`)
```python
import threading
from .config import DB_WRITE_CONCURRENCY

# 모듈 레벨 semaphore
db_write_semaphore = threading.Semaphore(DB_WRITE_CONCURRENCY)

# 사용
with db_write_semaphore:
    upsert_embeddings_batch(embeddings_data, run_id)
```

#### 3. Fallback 정책 변경 (`db.py`)
```python
# Before: 항상 fallback 허용
except Exception as e:
    logger.warning("Falling back to direct connection...")
    conn = psycopg2.connect(...)  # ❌

# After: 디버그 모드에서만 fallback
except Exception as e:
    if os.getenv("DB_ALLOW_DIRECT_FALLBACK", "false").lower() == "true":
        logger.warning("DEBUG MODE: Falling back to direct connection...")
        conn = psycopg2.connect(...)
    else:
        # 풀 상태 로깅
        pool_stats = get_pool_stats()
        logger.error(f"Pool exhausted. Stats: {pool_stats}")
        raise RuntimeError("Connection pool exhausted. Check for connection leaks.")
```

#### 4. 중복 체크 배치 처리 (`embedding.py`)
```python
# Before: 각 포스트마다 개별 쿼리
for post in posts:
    cur.execute("SELECT 1 FROM embeddings WHERE text_hash = %s", ...)

# After: 배치로 한 번에 체크
def check_existing_hashes_batch(text_hashes: List[str]) -> Set[str]:
    with get_db_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT text_hash FROM embeddings 
                WHERE text_hash = ANY(%s)
            """, (text_hashes,))
            return set(row[0] for row in cur.fetchall())
```

## [C] 설정값

### 권장 설정값
```python
# worker/pipeline/config.py
DB_WRITE_CONCURRENCY = int(os.getenv("DB_WRITE_CONCURRENCY", "3"))  # 동시 DB write 제한
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))  # 임베딩 배치 크기
DB_BATCH_SIZE = int(os.getenv("DB_BATCH_SIZE", "100"))  # DB 저장 배치 크기

# worker/pipeline/db.py
POOL_MINCONN = int(os.getenv("DB_POOL_MINCONN", "5"))
POOL_MAXCONN = int(os.getenv("DB_POOL_MAXCONN", "20"))
POOL_ACQUIRE_TIMEOUT = float(os.getenv("DB_POOL_ACQUIRE_TIMEOUT", "10.0"))
```

### 환경 변수 예시
```bash
# .env 또는 환경 변수
DB_WRITE_CONCURRENCY=3          # 동시 DB write 제한 (권장: 2-5)
DB_POOL_MINCONN=5               # 풀 최소 커넥션
DB_POOL_MAXCONN=20              # 풀 최대 커넥션
DB_POOL_ACQUIRE_TIMEOUT=10.0    # 풀 획득 타임아웃 (초)
EMBEDDING_BATCH_SIZE=64         # 임베딩 API 배치 크기
DB_BATCH_SIZE=100               # DB 저장 배치 크기
DB_ALLOW_DIRECT_FALLBACK=false  # 디버그 모드에서만 true
```

## [D] 재현/검증 명령어 및 성공 조건

### 스모크 테스트 스크립트
```python
# tests/test_db_pool_smoke.py
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.pipeline.db import get_connection_pool
from worker.pipeline.embedding import generate_embeddings
from worker.pipeline.db import create_pipeline_run

def test_embedding_pool():
    """200-1000건 임베딩 생성으로 풀 고갈 테스트"""
    run_id = create_pipeline_run("test", "running")
    
    # 200건만 처리 (빠른 테스트)
    stats = generate_embeddings(run_id, dry_run=False, max_docs=200)
    
    # 검증
    assert stats["errors"] == [], f"Errors occurred: {stats['errors']}"
    assert stats["embeddings_created"] > 0, "No embeddings created"
    
    # 풀 상태 확인
    pool = get_connection_pool()
    print(f"Pool stats: {pool.get_stats()}")
    
    return stats

if __name__ == "__main__":
    os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL")
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    stats = test_embedding_pool()
    print(f"✅ Test passed: {stats['embeddings_created']} embeddings created")
```

### 실행 명령어
```bash
# 1. 환경 변수 설정
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."
export DB_WRITE_CONCURRENCY=3

# 2. 스모크 테스트 실행
python3 tests/test_db_pool_smoke.py

# 3. 전체 테스트 실행 (로그 확인)
python3 worker/run_pipeline.py --mode=analyze 2>&1 | \
  grep -E "(PROGRESS|Pool|timeout|fallback|ERROR|WARNING)" | \
  tee /tmp/db_pool_test.log
```

### 성공 조건
- ✅ Pool acquire timeout 0회
- ✅ "Falling back to direct connection" 메시지 0회 (DB_ALLOW_DIRECT_FALLBACK=false일 때)
- ✅ 모든 배치가 정상 처리됨
- ✅ 평균 처리량 로그 출력됨
- ✅ 커넥션 풀 사용률이 maxconn 이하로 유지됨

### 실패 시 확인 사항
- 풀 상태 로그 확인
- 동시 실행 중인 커넥션 수 확인
- 커넥션 누수 확인 (풀 반환 누락)
