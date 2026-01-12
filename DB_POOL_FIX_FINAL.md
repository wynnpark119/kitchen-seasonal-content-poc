# DB 커넥션 풀 고갈 문제 최종 수정 완료

## [A] 원인 후보 Top 3

### 1. 함수 시작 시 커넥션 획득 후 장기 점유 (최우선) ✅ 수정됨
**위치**: `worker/pipeline/embedding.py:111` (이전)
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

**수정**: `embedding.py:124-155` - 포스트 목록 조회 후 즉시 반납, API 호출 시 커넥션 없음

### 2. 중복 체크를 위한 개별 쿼리 실행 ✅ 수정됨
**위치**: `worker/pipeline/embedding.py:176-184` (이전)
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

**수정**: `embedding.py:158-165` - `check_existing_hashes_batch()` 함수로 배치 처리

### 3. DB write 동시성 제한 없음 ✅ 수정됨
**위치**: `worker/pipeline/embedding.py:209` (이전)
```python
upsert_embeddings_batch(embeddings_data, run_id)  # 동시성 제한 없음
```
**근거**:
- 여러 배치가 동시에 실행될 수 있음
- 각 배치가 각각 커넥션을 획득
- 동시 실행 시 풀 고갈 가능

**수정**: `embedding.py:22` - `threading.Semaphore(DB_WRITE_CONCURRENCY)` 추가, `embedding.py:220, 258` - `with db_write_semaphore:` 사용

## [B] 수정안

### 변경 파일 리스트
1. `worker/pipeline/config.py` - 환경 변수 추가
2. `worker/pipeline/db.py` - 풀 설정, fallback 정책 변경, Json import 수정
3. `worker/pipeline/embedding.py` - 커넥션 점유 제거, 동시성 제한, 배치 처리
4. `tests/test_db_pool_smoke.py` - 스모크 테스트 추가

### 핵심 Diff

#### 1. 커넥션 점유 제거 (`embedding.py:124-155`)
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
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
            all_posts = cur.fetchall()
    finally:
        put_db_connection(conn)  # ✅ 즉시 반납
    
    # 2. 중복 체크 배치 처리 (짧은 트랜잭션)
    existing_hashes = check_existing_hashes_batch(text_hashes)
    
    # 3. API 호출 (커넥션 없음)
    embeddings = generate_embeddings_batch(batch, client)
    
    # 4. DB 저장 (짧은 트랜잭션, 동시성 제한)
    with db_write_semaphore:  # 동시성 제한
        upsert_embeddings_batch(embeddings_data, run_id)
```

#### 2. 중복 체크 배치 처리 (`embedding.py:158-165`)
```python
# Before: 각 포스트마다 개별 쿼리
for post in posts:
    cur.execute("SELECT 1 FROM embeddings WHERE text_hash = %s", ...)

# After: 배치로 한 번에 체크
def check_existing_hashes_batch(text_hashes: List[str], run_id: int) -> Set[str]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT text_hash 
                FROM embeddings 
                WHERE text_hash = ANY(%s)
            """, (text_hashes,))
            return set(row[0] for row in cur.fetchall())
    finally:
        put_db_connection(conn)  # ✅ 즉시 반납
```

#### 3. DB write 동시성 제한 (`embedding.py:22, 220, 258`)
```python
# 모듈 레벨 semaphore
db_write_semaphore = threading.Semaphore(DB_WRITE_CONCURRENCY)

# 사용
with db_write_semaphore:  # 동시성 제한 (기본값: 3)
    upsert_embeddings_batch(embeddings_data, run_id)
```

#### 4. Fallback 정책 변경 (`db.py:140-178`)
```python
# Before: 항상 fallback 허용
except Exception as e:
    logger.warning("Falling back to direct connection...")
    conn = psycopg2.connect(...)  # ❌

# After: 디버그 모드에서만 fallback
except Exception as e:
    if DB_ALLOW_DIRECT_FALLBACK:  # 환경 변수로 제어
        logger.warning("DEBUG MODE: Falling back to direct connection...")
        conn = psycopg2.connect(...)
    else:
        # 기본: 실패로 종료
        raise RuntimeError("Connection pool exhausted. Check for connection leaks.")
```

## [C] 설정값

### 권장 설정값
```python
# worker/pipeline/config.py
DB_WRITE_CONCURRENCY = 3          # 동시 DB write 제한 (권장: 2-5)
DB_POOL_MINCONN = 5               # 풀 최소 커넥션
DB_POOL_MAXCONN = 20              # 풀 최대 커넥션
DB_POOL_ACQUIRE_TIMEOUT = 10.0    # 풀 획득 타임아웃 (초)
EMBEDDING_BATCH_SIZE = 64         # 임베딩 API 배치 크기
DB_BATCH_SIZE = 100               # DB 저장 배치 크기
DB_ALLOW_DIRECT_FALLBACK = false  # 디버그 모드에서만 true
```

### 환경 변수 예시
```bash
# .env 또는 환경 변수
export DB_WRITE_CONCURRENCY=3          # 동시 DB write 제한 (권장: 2-5)
export DB_POOL_MINCONN=5               # 풀 최소 커넥션
export DB_POOL_MAXCONN=20              # 풀 최대 커넥션
export DB_POOL_ACQUIRE_TIMEOUT=10.0    # 풀 획득 타임아웃 (초)
export EMBEDDING_BATCH_SIZE=64         # 임베딩 API 배치 크기
export DB_BATCH_SIZE=100               # DB 저장 배치 크기
export DB_ALLOW_DIRECT_FALLBACK=false  # 디버그 모드에서만 true
```

## [D] 재현/검증 명령어 및 성공 조건

### 스모크 테스트 실행
```bash
# 1. 환경 변수 설정
export DATABASE_URL="postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway"
export OPENAI_API_KEY="your-openai-api-key-here"
export DB_WRITE_CONCURRENCY=3
export DB_ALLOW_DIRECT_FALLBACK=false

# 2. 스모크 테스트 실행 (200건)
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
python3 tests/test_db_pool_smoke.py

# 3. 전체 테스트 실행 (로그 확인)
python3 worker/run_pipeline.py --mode=analyze 2>&1 | \
  grep -E "(PROGRESS|Pool|timeout|fallback|ERROR|WARNING|completed)" | \
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

## 수정된 함수 목록

### `worker/pipeline/db.py`
- ✅ `get_db_connection()` - fallback 정책 변경
- ✅ `upsert_embeddings_batch()` - 새로 추가
- ✅ `upsert_embedding()` - 커넥션 반환 수정
- ✅ `upsert_cluster_assignment()` - 커넥션 반환 수정
- ✅ `upsert_topic_qa_brief()` - 커넥션 반환 수정
- ✅ `upsert_gsc_query()` - 커넥션 반환 수정
- ✅ `check_pgvector_available()` - 커넥션 반환 수정
- ✅ `create_pipeline_run()` - 커넥션 반환 수정

### `worker/pipeline/embedding.py`
- ✅ `check_existing_hashes_batch()` - 새로 추가 (배치 중복 체크)
- ✅ `generate_embeddings()` - 전체 재구성 (커넥션 점유 제거, 동시성 제한)

### `worker/pipeline/config.py`
- ✅ 환경 변수 추가 (DB_WRITE_CONCURRENCY, DB_POOL_*, DB_ALLOW_DIRECT_FALLBACK)

## 핵심 개선사항

1. **커넥션 점유 시간 최소화**: 함수 시작 시 획득 → 필요한 시점에만 획득
2. **API 호출과 DB 작업 분리**: API 호출 중 커넥션 점유 없음
3. **동시성 제한**: Semaphore로 DB write 동시성 제한 (기본값: 3)
4. **배치 처리**: 중복 체크 및 저장을 배치로 처리
5. **Fallback 정책**: 디버그 모드에서만 fallback 허용, 기본은 실패로 종료
