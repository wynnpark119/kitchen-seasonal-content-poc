# DB 적재 실패 원인 분석 및 수정안

## [1] 저장 경로 추적 (Call Chain)

### 전체 흐름
```
Apify Actor 실행 (MCP 또는 API)
  ↓
save_all_keywords_api.py:114 save_dataset()
  ↓
save_all_keywords_api.py:136 fetch_dataset_items()  # Apify API 호출
  ↓
save_all_keywords_api.py:144 process_apify_results(items, keyword, run_id)
  ↓
worker/pipeline/process_apify_results.py:114 upsert_reddit_posts_batch()
  ↓
worker/pipeline/db.py:239 upsert_reddit_posts_batch()
  ↓
worker/pipeline/db.py:61 get_db_connection()  # Connection pool 또는 직접 연결
  ↓
PostgreSQL INSERT/UPDATE 실행
```

### 실행 환경
- **서비스**: Railway Worker 서비스 (`worker/main.py`)
- **실행 명령**: `python -m worker.main` (railway-worker.json)
- **모드**: `WORKER_MODE=save_keywords` (또는 직접 `save_all_keywords_api.py` 실행)

### 핵심 파일 및 라인
1. **진입점**: `save_all_keywords_api.py:114` (`save_dataset()`)
2. **데이터 처리**: `worker/pipeline/process_apify_results.py:11` (`process_apify_results()`)
3. **DB 저장**: `worker/pipeline/db.py:239` (`upsert_reddit_posts_batch()`)
4. **연결 관리**: `worker/pipeline/db.py:28` (`get_connection_pool()`), `worker/pipeline/db.py:61` (`get_db_connection()`)

---

## [2] 실패 로그 핵심 (예상 에러 유형)

### A. 연결/인증 문제
**예상 에러 메시지**:
```
psycopg2.OperationalError: SSL connection required
psycopg2.OperationalError: connection to server at "xxx.railway.app" failed
psycopg2.OperationalError: FATAL: password authentication failed
```

**발생 위치**: `worker/pipeline/db.py:48-58` (connection pool 생성)

### B. 스키마/제약조건 문제
**예상 에러 메시지**:
```
psycopg2.errors.UndefinedTable: relation "raw_reddit_posts" does not exist
psycopg2.errors.UndefinedColumn: column "xxx" does not exist
psycopg2.errors.NotNullViolation: null value in column "xxx" violates not-null constraint
```

**발생 위치**: `worker/pipeline/db.py:289` (INSERT 실행)

### C. 데이터 정합성 문제
**예상 에러 메시지**:
```
psycopg2.errors.StringDataRightTruncation: value too long for type VARCHAR(50)
psycopg2.errors.InvalidTextRepresentation: invalid input syntax for type bigint
```

**발생 위치**: `worker/pipeline/db.py:266-279` (데이터 준비), `worker/pipeline/db.py:289` (INSERT 실행)

### D. 트랜잭션/락 문제
**예상 에러 메시지**:
```
psycopg2.errors.DeadlockDetected: deadlock detected
psycopg2.errors.QueryCanceled: canceling statement due to statement_timeout
```

**발생 위치**: `worker/pipeline/db.py:302` (commit)

---

## [3] 원인 후보 Top 3 (근거 포함)

### 🔴 원인 1순위: Railway PostgreSQL SSL 설정 누락 (A. 연결/인증 문제)

**근거**:
1. **코드 확인**: `worker/pipeline/db.py:44-46`에서 Railway URL 감지 시 SSL 추가하지만, 조건이 불완전:
   ```python
   if 'railway' in database_url.lower() and 'sslmode' not in database_url:
   ```
   - `railway` 문자열이 URL에 없을 수 있음 (예: `crossover.proxy.rlwy.net`)
   - `sslmode`가 이미 있지만 잘못된 값일 수 있음

2. **환경 변수 불일치**: 
   - `common/config.py:14`: `DATABASE_URL` 또는 `RAILWAY_DATABASE_URL`만 확인
   - `worker/pipeline/db.py:34-38`: 더 많은 변수 확인 (`POSTGRES_URL`, `POSTGRES_PRIVATE_URL`)
   - 두 모듈이 다른 환경 변수를 읽을 수 있음

3. **Connection Pool 초기화 실패**: 
   - `worker/pipeline/db.py:50-54`에서 pool 생성 실패 시 예외 발생
   - Fallback 로직(`worker/pipeline/db.py:69-78`)이 있지만 SSL 설정이 없을 수 있음

**확정을 위한 추가 로그**:
```python
logger.info(f"Database URL (masked): {database_url[:50]}...")
logger.info(f"SSL mode in URL: {'sslmode' in database_url}")
```

### 🟡 원인 2순위: 환경 변수 스코프 문제 (G. 실행 환경 문제)

**근거**:
1. **Railway 서비스별 변수 스코프**:
   - Worker 서비스에 `DATABASE_URL`이 제대로 주입되지 않았을 수 있음
   - PostgreSQL 서비스가 여러 개일 경우 (`Postgres`, `Postgres-tezK`) 잘못된 서비스의 URL을 읽을 수 있음

2. **환경 변수 읽기 순서 불일치**:
   - `common/config.py:14`: `DATABASE_URL` → `RAILWAY_DATABASE_URL`
   - `worker/pipeline/db.py:34-38`: `DATABASE_URL` → `RAILWAY_DATABASE_URL` → `POSTGRES_URL` → `POSTGRES_PRIVATE_URL`
   - 두 모듈이 다른 값을 읽을 수 있음

**확정을 위한 추가 로그**:
```python
logger.info(f"Env vars: DATABASE_URL={bool(os.getenv('DATABASE_URL'))}, "
            f"RAILWAY_DATABASE_URL={bool(os.getenv('RAILWAY_DATABASE_URL'))}, "
            f"POSTGRES_URL={bool(os.getenv('POSTGRES_URL'))}")
```

### 🟢 원인 3순위: Connection Pool 리소스 누수/타임아웃 (E. ORM/드라이버 사용 오류)

**근거**:
1. **Pool 반환 누락 가능성**:
   - `upsert_reddit_posts_batch()`에서 예외 발생 시 `put_db_connection()` 호출은 `finally`에 있음 (정상)
   - 하지만 `conn.close()` 대신 `put_db_connection()`을 호출해야 하는데, 일부 함수에서 `conn.close()` 직접 호출 (예: `upsert_gsc_query:408`)

2. **배치 처리 중 타임아웃**:
   - `execute_batch()`에서 대량 데이터 처리 시 `statement_timeout` 초과 가능
   - Railway PostgreSQL 기본 타임아웃이 짧을 수 있음

**확정을 위한 추가 로그**:
```python
logger.info(f"Pool stats: minconn={pool.minconn}, maxconn={pool.maxconn}")
logger.info(f"Batch size: {len(insert_data)}")
```

---

## [4] 수정안 (최소 변경 + 안전장치)

### 수정 1: Railway PostgreSQL SSL 설정 강화

**파일**: `worker/pipeline/db.py`

**변경 내용**:
1. Railway URL 감지 로직 개선 (더 넓은 패턴 매칭)
2. SSL 설정이 없으면 무조건 추가
3. 연결 실패 시 상세 로그 추가

```python
def get_connection_pool():
    """Get or create connection pool"""
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                database_url = (
                    os.getenv("DATABASE_URL") or 
                    os.getenv("RAILWAY_DATABASE_URL") or
                    os.getenv("POSTGRES_URL") or
                    os.getenv("POSTGRES_PRIVATE_URL")
                )
                if not database_url:
                    raise ValueError("DATABASE_URL not found in environment variables")
                
                # Railway PostgreSQL SSL 설정 강화
                # Railway URL 패턴: *.railway.app, *.proxy.rlwy.net, *.up.railway.app
                is_railway = any(pattern in database_url.lower() for pattern in [
                    'railway.app', 'rlwy.net', 'up.railway.app'
                ])
                
                if is_railway:
                    # SSL 모드 확인 및 추가
                    if 'sslmode' not in database_url.lower():
                        separator = '&' if '?' in database_url else '?'
                        database_url = f"{database_url}{separator}sslmode=require"
                        logger.info("Added sslmode=require to Railway database URL")
                    elif 'sslmode=disable' in database_url.lower():
                        # sslmode=disable이면 require로 변경
                        database_url = database_url.replace('sslmode=disable', 'sslmode=require')
                        logger.warning("Changed sslmode from disable to require for Railway")
                
                # 연결 테스트를 위한 로그 (민감 정보 마스킹)
                url_masked = database_url.split('@')[-1] if '@' in database_url else database_url[:50]
                logger.info(f"Connecting to database: ...@{url_masked}")
                logger.debug(f"SSL mode: {'sslmode' in database_url.lower()}")
                
                try:
                    # Connection pool 생성 (min 2, max 10)
                    _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=2,
                        maxconn=10,
                        dsn=database_url,
                        connect_timeout=10  # 연결 타임아웃 10초
                    )
                    logger.info("Connection pool created successfully")
                except Exception as e:
                    logger.error(f"Failed to create connection pool: {e}")
                    logger.error(f"Database URL pattern: {url_masked}")
                    raise
    return _connection_pool
```

### 수정 2: 배치 처리 안전장치 강화

**파일**: `worker/pipeline/db.py`

**변경 내용**:
1. 배치 크기 제한 (한 번에 너무 많은 데이터 처리 방지)
2. 재시도 로직 적용
3. 상세 에러 로깅

```python
def upsert_reddit_posts_batch(posts_data: List[Dict[str, Any]], run_id: int) -> Dict[str, int]:
    """Batch upsert Reddit posts (성능 개선)"""
    if not posts_data:
        return {"inserted": 0, "updated": 0, "errors": 0}
    
    # 배치 크기 제한 (한 번에 최대 500개)
    BATCH_SIZE_LIMIT = 500
    if len(posts_data) > BATCH_SIZE_LIMIT:
        logger.warning(f"Batch size {len(posts_data)} exceeds limit {BATCH_SIZE_LIMIT}, splitting...")
        # 재귀적으로 분할 처리
        stats = {"inserted": 0, "updated": 0, "errors": 0}
        for i in range(0, len(posts_data), BATCH_SIZE_LIMIT):
            batch = posts_data[i:i + BATCH_SIZE_LIMIT]
            batch_stats = upsert_reddit_posts_batch(batch, run_id)
            stats["inserted"] += batch_stats["inserted"]
            stats["updated"] += batch_stats["updated"]
            stats["errors"] += batch_stats["errors"]
        return stats
    
    conn = None
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    
    @retry_db_operation(max_retries=3, backoff=2.0)
    def _execute_batch_insert():
        nonlocal conn, stats, insert_data
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # 배치 INSERT
            execute_batch(cur, """
                INSERT INTO raw_reddit_posts (
                    reddit_post_id, subreddit, title, body, author,
                    created_utc, upvotes, num_comments, permalink, url,
                    keyword, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reddit_post_id) DO UPDATE SET
                    upvotes = EXCLUDED.upvotes,
                    num_comments = EXCLUDED.num_comments,
                    updated_at = CURRENT_TIMESTAMP
            """, insert_data, page_size=100)
            
            stats["inserted"] = len(insert_data)
            conn.commit()
            logger.info(f"Batch upserted {stats['inserted']} posts, {stats['errors']} errors")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Batch insert error: {e}", exc_info=True)
            # 첫 번째 실패한 레코드 샘플 로깅
            if insert_data:
                sample = insert_data[0]
                logger.error(f"Sample data (first record): post_id={sample[0]}, "
                           f"title_len={len(sample[2]) if sample[2] else 0}, "
                           f"body_len={len(sample[3]) if sample[3] else 0}")
            raise
    
    try:
        # 배치 처리용 데이터 준비
        insert_data = []
        import time as time_module
        
        for post_data in posts_data:
            try:
                post_id = str(post_data.get('id', '')).strip()
                if not post_id:
                    stats["errors"] += 1
                    continue
                
                created_utc = post_data.get('created_utc', 0)
                if not isinstance(created_utc, int) or created_utc <= 0:
                    created_utc = int(time_module.time())
                
                insert_data.append((
                    post_id,
                    (post_data.get('subreddit', '') or 'unknown')[:100],
                    (post_data.get('title', '') or 'Untitled')[:10000],
                    (post_data.get('selftext', '') or '')[:50000] or None,
                    (post_data.get('author', '') or '')[:100] or None,
                    created_utc,
                    max(0, int(post_data.get('ups', 0))),
                    max(0, int(post_data.get('num_comments', 0))),
                    (post_data.get('permalink', '') or '')[:5000] or None,
                    (post_data.get('url', '') or '')[:5000] or None,
                    (post_data.get('keyword', '') or '')[:200],
                    Json(post_data)
                ))
            except Exception as e:
                logger.error(f"Error preparing post data {post_data.get('id', 'unknown')}: {e}")
                stats["errors"] += 1
                continue
        
        if not insert_data:
            return stats
        
        # 배치 INSERT 실행 (재시도 포함)
        _execute_batch_insert()
        
    except Exception as e:
        logger.error(f"Batch upsert error (final): {e}", exc_info=True)
        stats["errors"] = len(posts_data) - stats["inserted"]
        # 에러를 다시 raise하지 않고 통계만 반환 (부분 성공 허용)
        # raise  # 주석 처리: 부분 성공 허용
    finally:
        if conn:
            put_db_connection(conn)
    
    return stats
```

### 수정 3: 환경 변수 확인 로직 통일

**파일**: `common/config.py`

**변경 내용**:
1. `worker/pipeline/db.py`와 동일한 환경 변수 읽기 순서 적용
2. 로깅 추가

```python
# Database 설정
DATABASE_URL = (
    os.getenv("DATABASE_URL") or 
    os.getenv("RAILWAY_DATABASE_URL") or
    os.getenv("POSTGRES_URL") or
    os.getenv("POSTGRES_PRIVATE_URL")
)
```

---

## [5] 검증 체크리스트

### 로컬 검증

1. **환경 변수 확인**:
```bash
# Railway DATABASE_URL 복사 후 로컬에서 테스트
export DATABASE_URL="postgresql://postgres:xxx@xxx.railway.app:5432/railway"
python -c "from worker.pipeline.db import get_db_connection; conn = get_db_connection(); print('✅ 연결 성공'); conn.close()"
```

2. **SSL 연결 테스트**:
```bash
# SSL 모드 확인
python -c "
import os
url = os.getenv('DATABASE_URL', '')
print(f'SSL mode in URL: {\"sslmode\" in url.lower()}')
print(f'URL pattern: {url[:50]}...')
"
```

3. **배치 저장 테스트**:
```python
# test_batch_save.py
from worker.pipeline.db import create_pipeline_run, upsert_reddit_posts_batch

run_id = create_pipeline_run("test", "running")
test_posts = [
    {
        'id': 'test_1',
        'subreddit': 'test',
        'title': 'Test Post',
        'selftext': 'Test body',
        'author': 'testuser',
        'created_utc': 1234567890,
        'ups': 10,
        'num_comments': 5,
        'permalink': '/r/test/test_1',
        'url': 'https://reddit.com/r/test/test_1',
        'keyword': 'test keyword'
    }
]
stats = upsert_reddit_posts_batch(test_posts, run_id)
print(f"✅ 저장 완료: {stats}")
```

### Railway 배포 후 확인

1. **Worker 로그 확인**:
```bash
# Railway 대시보드 > Worker 서비스 > Logs
# 다음 메시지 확인:
# - "Connection pool created successfully"
# - "Added sslmode=require to Railway database URL" (필요시)
# - "Batch upserted X posts"
```

2. **에러 로그 확인**:
```bash
# 다음 에러가 없는지 확인:
# - "Failed to create connection pool"
# - "Batch insert error"
# - "SSL connection required"
```

3. **데이터 확인**:
```sql
-- Railway PostgreSQL 쿼리 실행
SELECT COUNT(*) FROM raw_reddit_posts;
SELECT keyword, COUNT(*) FROM raw_reddit_posts GROUP BY keyword ORDER BY COUNT(*) DESC LIMIT 10;
```

4. **환경 변수 확인**:
```bash
# Railway 대시보드 > Worker 서비스 > Variables
# 다음 변수가 설정되어 있는지 확인:
# - DATABASE_URL (또는 RAILWAY_DATABASE_URL)
# - APIFY_API_TOKEN (save_keywords 모드 사용 시)
```

5. **헬스체크**:
```python
# Railway Worker 서비스에서 실행
python -c "
from worker.pipeline.db import get_db_connection, check_pgvector_available
conn = get_db_connection()
cur = conn.cursor()
cur.execute('SELECT 1')
print('✅ DB 연결 성공')
cur.close()
conn.close()
"
```

---

## 추가 권장사항

### 1. 에러 모니터링 강화
- 실패한 레코드를 별도 테이블(`failed_reddit_posts`)에 저장
- Railway 로그에 에러 알림 설정

### 2. 성능 모니터링
- 배치 처리 시간 로깅
- Connection pool 사용률 모니터링

### 3. 재시도 정책
- 현재 `@retry_db_operation` 데코레이터 사용 중 (좋음)
- 배치 실패 시 개별 레코드 재시도 옵션 추가 고려
