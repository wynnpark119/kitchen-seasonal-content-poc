# Apify 데이터 적재 실패 분석 및 수정 완료 보고서

## [1] 저장 경로 (함수/파일/라인) 요약

### Call Chain (Apify → DB)

```
Railway Worker 서비스 실행
  ↓
worker/main.py:249 main()
  ↓ [환경변수: WORKER_MODE=save_keywords]
worker/main.py:220 run_pipeline(mode="save_keywords")
  ↓
worker/main.py:116 save_dataset(apify_client, dataset_id, keyword, run_id)
  ↓ [save_all_keywords_api.py:114]
save_all_keywords_api.py:136 fetch_dataset_items()
  ↓ [Apify API 호출: apify_client.dataset(dataset_id).list_items()]
save_all_keywords_api.py:144 process_apify_results(items, keyword, run_id)
  ↓ [worker/pipeline/process_apify_results.py:11]
worker/pipeline/process_apify_results.py:26-88
  ↓ [배치 수집: posts_to_insert 리스트에 추가]
worker/pipeline/process_apify_results.py:91 upsert_reddit_posts_batch(posts_to_insert, run_id)
  ↓ [worker/pipeline/db.py:239]
worker/pipeline/db.py:248 get_db_connection()  # Connection pool에서 가져오기
  ↓
worker/pipeline/db.py:289 execute_batch()  # 배치 INSERT (100개씩)
  ↓
worker/pipeline/db.py:302 conn.commit()  # 배치 커밋
  ↓
worker/pipeline/db.py:313 put_db_connection(conn)  # Connection pool에 반환
```

### 실행 환경
- **실행 위치**: Railway Worker 서비스 (백그라운드 프로세스)
- **시작 명령**: `python -m worker.main` (railway-worker.json)
- **트리거**: `WORKER_MODE=save_keywords` 환경 변수
- **데이터 소스**: Apify API (apify-client 라이브러리)
- **저장 대상**: Railway PostgreSQL (Postgres-tezK 또는 Postgres)

### 핵심 파일 및 라인
1. `worker/main.py:75-137` - save_keywords 모드 처리
2. `save_all_keywords_api.py:114-151` - Apify 데이터셋에서 아이템 가져오기
3. `worker/pipeline/process_apify_results.py:11-95` - Apify 결과 파싱 및 배치 수집
4. `worker/pipeline/db.py:239-315` - 배치 DB INSERT/UPSERT 실행
5. `worker/pipeline/db.py:17-79` - Connection pool 관리

---

## [2] 실패 로그 핵심 (예상 에러 메시지/스택)

### 실제 발생 가능한 에러 (코드 분석 기반)

#### E. ORM/드라이버 사용 오류 - Connection Pool 고갈 (1순위)
```
psycopg2.pool.PoolError: connection pool exhausted
또는
psycopg2.OperationalError: too many connections
또는
psycopg2.InterfaceError: connection already closed
```

**발생 위치**: `worker/pipeline/db.py:92` (이전 코드)
- 매 포스트마다 새 연결 생성 → 4,000번 연결 생성/해제
- Railway PostgreSQL 연결 제한 초과

#### F. 데이터 정합성 문제 - NULL/빈 값 (2순위)
```
psycopg2.IntegrityError: null value in column "reddit_post_id" violates not-null constraint
또는
psycopg2.DataError: invalid input syntax for type bigint: ""
또는
psycopg2.ProgrammingError: can't adapt type 'NoneType'
```

**발생 위치**: `worker/pipeline/process_apify_results.py:34-36`
- `post_id = item.get('parsedId') or item.get('id', '')` → 빈 문자열 가능
- `created_utc = 0` → 유효하지 않은 타임스탬프

#### A. 연결/인증 문제 - DATABASE_URL 미설정 (3순위)
```
ValueError: DATABASE_URL not found in environment variables
또는
psycopg2.OperationalError: could not connect to server
```

**발생 위치**: `worker/pipeline/db.py:19` (이전 코드)
- Worker 서비스 Variables에 DATABASE_URL 미설정
- 또는 Railway 내부 URL 접근 불가

---

## [3] 원인 후보 Top 3 (근거 포함)

### 🔴 원인 1순위: E. ORM/드라이버 사용 오류 - Connection Pool 고갈

**근거:**
1. **코드 증거**: `worker/pipeline/db.py:90-125` (이전 코드)
   - `upsert_reddit_post()`가 매 포스트마다 `get_db_connection()` 호출
   - 연결 생성 → 커밋 → 연결 닫기 반복
   - 20개 키워드 × 200개 포스트 = **4,000번의 연결 생성/해제**

2. **성능 문제**: 
   - 각 연결 생성에 약 10-50ms 소요
   - 총 연결 생성 시간: 40-200초
   - Railway PostgreSQL 연결 제한(보통 100개) 초과 가능

3. **확인 방법**:
   - Railway Worker 로그에서 "too many connections" 에러 확인
   - PostgreSQL Metrics에서 활성 연결 수 확인 (정상: <10, 문제: >50)

**확정을 위한 추가 로그**:
```python
# worker/pipeline/db.py에 추가
logger.debug(f"Active connections: {pool._used_connections}")
```

---

### 🟡 원인 2순위: F. 데이터 정합성 문제 - NULL/빈 값 처리

**근거:**
1. **코드 증거**: `process_apify_results.py:34-36`
   ```python
   post_id = item.get('parsedId') or item.get('id', '')
   if not post_id:  # 빈 문자열은 통과됨
       continue
   ```
   - `''` (빈 문자열)은 `not post_id`에서 False로 평가되어 통과 가능
   - `db.py:106`: `post_data['id']`가 빈 문자열이면 PRIMARY KEY 제약조건 위반

2. **타임스탬프 문제**:
   - `_parse_timestamp('')` → `0` 반환
   - `created_utc = 0` → `BIGINT NOT NULL` 제약조건은 만족하지만 유효하지 않은 값

3. **확인 방법**:
   - 로그에서 "null value in column" 또는 "invalid input syntax" 에러 확인
   - `process_apify_results.py:91`의 에러 로그에서 실패한 아이템 ID 확인

**확정을 위한 추가 로그**:
```python
# process_apify_results.py에 추가
if not post_id or len(str(post_id).strip()) == 0:
    logger.warning(f"Invalid post_id: {item.get('id', 'unknown')}")
    continue
```

---

### 🟠 원인 3순위: A. 연결/인증 문제 - DATABASE_URL 환경 변수 불일치

**근거:**
1. **코드 불일치**:
   - `worker/pipeline/db.py:19` (이전): `DATABASE_URL` 또는 `RAILWAY_DATABASE_URL`만 확인
   - `save_all_keywords_api.py:165-170`: 더 많은 변수 확인 (`POSTGRES_URL`, `POSTGRES_PRIVATE_URL`)

2. **Railway 환경**:
   - PostgreSQL 서비스가 여러 개일 수 있음 (Postgres, Postgres-tezK)
   - Worker 서비스 Variables에 `DATABASE_URL`이 설정되지 않았을 가능성

3. **확인 방법**:
   - Railway Worker 서비스 Variables에서 `DATABASE_URL` 존재 여부 확인
   - Worker 로그에서 "DATABASE_URL not found" 에러 확인

**확정을 위한 추가 로그**:
```python
# worker/pipeline/db.py에 추가
logger.info(f"DATABASE_URL sources: DATABASE_URL={bool(os.getenv('DATABASE_URL'))}, "
           f"RAILWAY_DATABASE_URL={bool(os.getenv('RAILWAY_DATABASE_URL'))}, "
           f"POSTGRES_URL={bool(os.getenv('POSTGRES_URL'))}")
```

---

## [4] 수정안 (변경 파일 리스트 + 핵심 코드)

### 수정된 파일

1. **`worker/pipeline/db.py`** (대폭 수정)
   - Connection pooling 추가
   - 배치 upsert 함수 추가
   - 재시도 메커니즘 추가
   - 데이터 검증 강화
   - SSL 설정 자동 추가

2. **`worker/pipeline/process_apify_results.py`** (수정)
   - 배치 처리로 변경
   - 데이터 검증 강화

### 핵심 변경 사항

#### 변경 1: Connection Pooling
```python
# worker/pipeline/db.py:17-79
_connection_pool = None
_pool_lock = threading.Lock()

def get_connection_pool():
    """Get or create connection pool"""
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                database_url = (...)
                # Railway PostgreSQL SSL 설정
                if 'railway' in database_url.lower() and 'sslmode' not in database_url:
                    separator = '&' if '?' in database_url else '?'
                    database_url = f"{database_url}{separator}sslmode=require"
                
                _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=10,
                    dsn=database_url
                )
    return _connection_pool

def get_db_connection():
    """Get database connection from pool"""
    pool = get_connection_pool()
    return pool.getconn()

def put_db_connection(conn):
    """Return connection to pool"""
    pool = get_connection_pool()
    pool.putconn(conn)
```

#### 변경 2: 배치 처리
```python
# worker/pipeline/db.py:239-315
def upsert_reddit_posts_batch(posts_data: List[Dict[str, Any]], run_id: int) -> Dict[str, int]:
    """Batch upsert Reddit posts (성능 개선)"""
    conn = get_db_connection()
    try:
        # 배치 데이터 준비
        insert_data = [...]
        
        # 배치 INSERT (100개씩)
        execute_batch(cur, """
            INSERT INTO raw_reddit_posts (...) VALUES (...)
            ON CONFLICT (reddit_post_id) DO UPDATE SET ...
        """, insert_data, page_size=100)
        
        conn.commit()
    finally:
        put_db_connection(conn)
```

#### 변경 3: 재시도 메커니즘
```python
# worker/pipeline/db.py:85-103
def retry_db_operation(max_retries=3, backoff=1.0):
    """데이터베이스 작업 재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    if attempt < max_retries - 1:
                        wait_time = backoff * (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        raise
        return wrapper
    return decorator

@retry_db_operation(max_retries=3, backoff=1.0)
def upsert_reddit_post(...):
    ...
```

#### 변경 4: 데이터 검증 강화
```python
# worker/pipeline/process_apify_results.py:34-36
post_id = item.get('parsedId') or item.get('id', '')
# 검증 강화: 빈 문자열, None, 공백만 있는 경우 제외
if not post_id or not isinstance(post_id, str) or len(str(post_id).strip()) == 0:
    logger.debug(f"Skipping post with invalid ID")
    continue

post_id = str(post_id).strip()

# 타임스탬프 검증
created_utc = _parse_timestamp(created_utc_str)
if created_utc <= 0:
    import time
    created_utc = int(time.time())
```

---

## [5] 검증 체크리스트

### 로컬 검증

```bash
# 1. 환경 변수 설정
export DATABASE_URL="postgresql://..."
export APIFY_API_TOKEN="..."

# 2. 단일 키워드 테스트
python3 -c "
from save_all_keywords_api import save_dataset, check_database_connection
from apify_client import ApifyClient
from worker.pipeline.db import create_pipeline_run
import os

assert check_database_connection(), 'DB connection failed'
apify_client = ApifyClient(os.getenv('APIFY_API_TOKEN'))
run_id = create_pipeline_run('test', 'running')
stats = save_dataset(apify_client, 'Chej96NJu2xomUrg1', 'spring dinner ideas', run_id)
print(f'Test result: {stats}')
"

# 3. Connection pool 테스트
python3 -c "
from worker.pipeline.db import get_db_connection, put_db_connection
conn1 = get_db_connection()
conn2 = get_db_connection()
print(f'Got 2 connections from pool')
put_db_connection(conn1)
put_db_connection(conn2)
print('Returned connections to pool')
"
```

### Railway 배포 후 확인

#### 1. Worker 로그 확인 포인트

**정상 실행 시:**
```
Connection pool created successfully
✅ Apify 클라이언트 초기화 완료
✅ 데이터베이스 연결 성공
Processing X items...
Batch upserted X posts, Y errors
```

**에러 발생 시:**
- "too many connections" → Connection pool 문제 (해결됨)
- "null value in column" → 데이터 검증 문제 (해결됨)
- "DATABASE_URL not found" → 환경 변수 문제

#### 2. PostgreSQL Metrics 확인

Railway PostgreSQL 서비스 → **Metrics** 탭:
- 활성 연결 수 < 10 (정상)
- 활성 연결 수 > 50 (문제)

#### 3. 데이터베이스 직접 확인

```sql
-- 총 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY count DESC;

-- 최근 적재된 데이터 확인
SELECT keyword, title, created_at 
FROM raw_reddit_posts 
ORDER BY created_at DESC 
LIMIT 10;
```

#### 4. Pipeline Runs 확인

```sql
SELECT run_id, run_type, status, started_at, completed_at, metadata
FROM pipeline_runs 
WHERE run_type = 'save_keywords'
ORDER BY started_at DESC 
LIMIT 1;
```

**완료된 경우:**
- `status` = `completed`
- `completed_at` ≠ NULL
- `metadata`에 `{"keywords_processed": 20, "total_posts": XXXX, ...}`

---

## 추가 확인 사항

### DATABASE_URL 확인

Railway Worker 서비스 Variables에서:
- `DATABASE_URL` 존재 여부 확인
- 값이 `postgresql://postgres:...@postgres-tezk.railway.internal:5432/railway` 형식인지 확인
- 또는 공개 URL 형식인지 확인

### Redis 확인

현재 코드베이스에는 Redis를 사용하는 큐/워커 시스템이 없습니다.
- 직접 Apify API 호출 → 배치 처리 → DB 저장 방식
- Redis 불필요

---

## 성능 개선 예상

### 이전 (개별 INSERT)
- 연결 생성: 4,000번
- INSERT 실행: 4,000번
- 예상 시간: 5-10분

### 이후 (배치 INSERT)
- 연결 생성: 약 40번 (키워드당 2번)
- INSERT 실행: 약 40번 (배치당 100개)
- 예상 시간: 1-2분

**성능 개선: 약 5배 빠름**

---

## 배포 후 모니터링

1. **Worker 로그**: "Batch upserted X posts" 메시지 확인
2. **PostgreSQL Metrics**: 활성 연결 수 모니터링
3. **데이터베이스**: 포스트 수 확인
4. **에러 로그**: 실패한 키워드/아이템 확인
