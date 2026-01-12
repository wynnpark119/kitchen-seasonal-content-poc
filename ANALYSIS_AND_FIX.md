# Apify 데이터 적재 실패 분석 및 수정안

## [1] 저장 경로 (함수/파일/라인) 요약

### Call Chain 추적

```
Railway Worker 서비스 실행
  ↓
worker/main.py:249 main()
  ↓
worker/main.py:220 run_pipeline(mode="save_keywords")
  ↓
worker/main.py:116 save_dataset(apify_client, dataset_id, keyword, run_id)
  ↓ (save_all_keywords_api.py:114)
save_all_keywords_api.py:136 fetch_dataset_items()  # Apify API 호출
  ↓
save_all_keywords_api.py:144 process_apify_results(items, keyword, run_id)
  ↓ (worker/pipeline/process_apify_results.py:11)
worker/pipeline/process_apify_results.py:62 upsert_reddit_post(post_data, run_id)
  ↓ (worker/pipeline/db.py:90)
worker/pipeline/db.py:92 get_db_connection()  # 매번 새 연결 생성
  ↓
worker/pipeline/db.py:95-119 psycopg2.execute(INSERT ... ON CONFLICT)
  ↓
worker/pipeline/db.py:119 conn.commit()  # 각 포스트마다 커밋
```

### 실행 환경
- **실행 위치**: Railway Worker 서비스 (백그라운드 프로세스)
- **시작 명령**: `python -m worker.main` (railway-worker.json)
- **트리거**: `WORKER_MODE=save_keywords` 환경 변수

### 핵심 파일
1. `worker/main.py:75-137` - save_keywords 모드 처리
2. `save_all_keywords_api.py:114-151` - Apify 데이터셋에서 아이템 가져오기
3. `worker/pipeline/process_apify_results.py:11-95` - Apify 결과 파싱 및 매핑
4. `worker/pipeline/db.py:90-125` - DB INSERT/UPSERT 실행

---

## [2] 실패 로그 핵심 (예상 에러 메시지/스택)

### 예상 실패 유형별 에러

#### A. 연결/인증 문제
```
ValueError: DATABASE_URL not found in environment variables
또는
psycopg2.OperationalError: could not connect to server
또는
psycopg2.OperationalError: connection to server at "..." failed: Connection refused
```

#### C. 제약조건 위반
```
psycopg2.IntegrityError: null value in column "reddit_post_id" violates not-null constraint
또는
psycopg2.IntegrityError: duplicate key value violates unique constraint "uk_reddit_post_id"
```

#### E. ORM/드라이버 사용 오류
```
psycopg2.OperationalError: too many connections
또는
psycopg2.InterfaceError: connection already closed
또는
psycopg2.DatabaseError: current transaction is aborted, commands ignored until end of transaction block
```

#### F. 데이터 정합성 문제
```
psycopg2.DataError: invalid input syntax for type bigint: ""
또는
psycopg2.DataError: invalid input syntax for type jsonb
또는
psycopg2.ProgrammingError: can't adapt type 'NoneType'
```

---

## [3] 원인 후보 Top 3 (근거 포함)

### 🔴 원인 1순위: E. ORM/드라이버 사용 오류 - Connection Pool 고갈

**근거:**
- `worker/pipeline/db.py:90-125`: `upsert_reddit_post()`가 **매 포스트마다** `get_db_connection()` 호출 → 새 연결 생성 → 커밋 → 연결 닫기
- 20개 키워드 × 200개 포스트 = **4,000번의 연결 생성/해제**
- Railway PostgreSQL 연결 제한(보통 100개) 초과 가능성
- `process_apify_results.py:26`: 각 아이템을 순차 처리하며 매번 새 연결

**코드 증거:**
```python
# worker/pipeline/db.py:90-125
def upsert_reddit_post(...):
    conn = get_db_connection()  # ← 매번 새 연결
    try:
        # INSERT 실행
        conn.commit()
    finally:
        conn.close()  # ← 매번 연결 닫기
```

**확인 방법:**
- Railway Worker 로그에서 "too many connections" 또는 "connection pool exhausted" 에러 확인
- PostgreSQL 서비스 Metrics에서 활성 연결 수 확인

---

### 🟡 원인 2순위: F. 데이터 정합성 문제 - NULL/빈 값 처리

**근거:**
- `process_apify_results.py:34`: `post_id = item.get('parsedId') or item.get('id', '')`
  - 빈 문자열(`''`)이 반환될 수 있음
- `process_apify_results.py:46`: `created_utc = item.get('createdAt') or item.get('created_utc', '')`
  - 빈 문자열이 `_parse_timestamp()`에 전달되면 `0` 반환
- `db.py:111`: `post_data.get('created_utc', 0)` → `BIGINT NOT NULL` 제약조건은 만족하지만, `0`은 유효하지 않은 타임스탬프
- `db.py:117`: `Json(post_data)` → None 값이 포함된 dict를 JSONB로 변환 시 문제 가능

**코드 증거:**
```python
# process_apify_results.py:34-36
post_id = item.get('parsedId') or item.get('id', '')
if not post_id:  # 빈 문자열은 통과됨
    continue  # 하지만 빈 문자열은 통과될 수 있음
```

**확인 방법:**
- 로그에서 "null value in column" 또는 "invalid input syntax" 에러 확인
- `process_apify_results.py:91`의 에러 로그에서 실패한 아이템 ID 확인

---

### 🟠 원인 3순위: A. 연결/인증 문제 - DATABASE_URL 환경 변수 불일치

**근거:**
- `worker/pipeline/db.py:19`: `DATABASE_URL` 또는 `RAILWAY_DATABASE_URL`만 확인
- `save_all_keywords_api.py:165-170`: 더 많은 환경 변수 확인 (`POSTGRES_URL`, `POSTGRES_PRIVATE_URL`)
- Railway에서 PostgreSQL 서비스가 여러 개일 수 있음 (Postgres, Postgres-tezK)
- Worker 서비스 Variables에 `DATABASE_URL`이 설정되지 않았을 가능성

**코드 증거:**
```python
# worker/pipeline/db.py:19
database_url = os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL")
# save_all_keywords_api.py:165-170는 더 많은 변수 확인
```

**확인 방법:**
- Railway Worker 서비스 Variables에서 `DATABASE_URL` 존재 여부 확인
- Worker 로그에서 "DATABASE_URL not found" 에러 확인

---

## [4] 수정안 (diff 또는 변경 파일 리스트 + 핵심 코드)

### 수정 1: Connection Pooling 및 배치 처리

**파일**: `worker/pipeline/db.py`

```python
# Connection pool 추가 및 배치 upsert 지원
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_batch
import threading

# 전역 connection pool
_connection_pool = None
_pool_lock = threading.Lock()

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
                
                # Connection pool 생성 (min 2, max 10)
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

def upsert_reddit_posts_batch(posts_data: List[Dict[str, Any]], run_id: int) -> Dict[str, int]:
    """Batch upsert Reddit posts (성능 개선)"""
    if not posts_data:
        return {"inserted": 0, "updated": 0, "errors": 0}
    
    conn = None
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 배치 처리용 데이터 준비
        insert_data = []
        for post_data in posts_data:
            try:
                insert_data.append((
                    post_data['id'],
                    post_data.get('subreddit', ''),
                    post_data.get('title', '')[:10000],  # TEXT 제한 대비
                    post_data.get('selftext', '')[:50000] if post_data.get('selftext') else None,
                    post_data.get('author', '')[:100] if post_data.get('author') else None,
                    max(0, int(post_data.get('created_utc', 0))),  # 음수 방지
                    max(0, int(post_data.get('ups', 0))),
                    max(0, int(post_data.get('num_comments', 0))),
                    post_data.get('permalink', '')[:5000] if post_data.get('permalink') else None,
                    post_data.get('url', '')[:5000] if post_data.get('url') else None,
                    post_data.get('keyword', '')[:200],
                    Json(post_data)
                ))
            except Exception as e:
                logger.error(f"Error preparing post data {post_data.get('id', 'unknown')}: {e}")
                stats["errors"] += 1
                continue
        
        if not insert_data:
            return stats
        
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
        
        stats["inserted"] = cur.rowcount
        conn.commit()
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Batch upsert error: {e}", exc_info=True)
        stats["errors"] += len(posts_data)
        raise
    finally:
        if conn:
            put_db_connection(conn)
    
    return stats
```

### 수정 2: 데이터 검증 강화

**파일**: `worker/pipeline/process_apify_results.py`

```python
def process_apify_results(items: List[Dict[str, Any]], keyword: str, run_id: int) -> Dict[str, Any]:
    """Process Apify MCP results and save to database"""
    stats = {
        "posts_collected": 0,
        "comments_collected": 0,
        "errors": []
    }
    
    posts_to_insert = []
    comments_to_insert = []
    
    logger.info(f"Processing {len(items)} items for keyword: {keyword}")
    
    for item in items:
        try:
            data_type = item.get('dataType') or item.get('kind', 'post')
            
            if data_type == 'post':
                post_id = item.get('parsedId') or item.get('id', '')
                # 검증 강화
                if not post_id or not isinstance(post_id, str) or len(post_id.strip()) == 0:
                    logger.warning(f"Skipping post with invalid ID: {item.get('id', 'unknown')}")
                    continue
                
                # 타임스탬프 검증
                created_utc = _parse_timestamp(item.get('createdAt') or item.get('created_utc', ''))
                if created_utc <= 0:
                    logger.warning(f"Post {post_id} has invalid timestamp, using current time")
                    import time
                    created_utc = int(time.time())
                
                post_data = {
                    'id': post_id.strip(),
                    'subreddit': (item.get('subredditName') or item.get('subreddit', '') or 'unknown')[:100],
                    'title': (item.get('title', '') or 'Untitled')[:10000],
                    'selftext': (item.get('body') or item.get('text') or item.get('selftext', '') or '')[:50000],
                    'author': (item.get('authorName') or item.get('author', '') or '')[:100] or None,
                    'created_utc': created_utc,
                    'ups': max(0, int(item.get('upVotes') or item.get('upvotes') or item.get('score', 0))),
                    'num_comments': max(0, int(item.get('commentsCount') or item.get('num_comments', 0))),
                    'permalink': (item.get('postUrl') or item.get('permalink') or item.get('url', '') or '')[:5000] or None,
                    'url': (item.get('contentUrl') or item.get('postUrl') or item.get('url', '') or '')[:5000] or None,
                    'keyword': keyword[:200]
                }
                
                posts_to_insert.append(post_data)
                
            elif data_type == 'comment':
                comment_id = item.get('id', '')
                post_id = item.get('parsedPostId') or item.get('postId', '')
                
                if not comment_id or not post_id or len(comment_id.strip()) == 0 or len(post_id.strip()) == 0:
                    continue
                
                created_utc = _parse_timestamp(item.get('commentCreatedAt') or item.get('createdAt') or item.get('created_utc', ''))
                if created_utc <= 0:
                    import time
                    created_utc = int(time.time())
                
                comment_data = {
                    'id': comment_id.strip(),
                    'body': (item.get('body') or item.get('text', '') or '')[:50000],
                    'author': (item.get('authorName') or item.get('author', '') or '')[:100] or None,
                    'created_utc': created_utc,
                    'ups': max(0, int(item.get('commentUpVotes') or item.get('upvotes') or item.get('score', 0))),
                    'is_top': False,
                    'post_id': post_id.strip()
                }
                
                comments_to_insert.append(comment_data)
                
        except Exception as e:
            logger.error(f"Error processing item {item.get('id', 'unknown')}: {e}", exc_info=True)
            stats["errors"].append(str(e))
    
    # 배치로 저장
    try:
        if posts_to_insert:
            batch_stats = upsert_reddit_posts_batch(posts_to_insert, run_id)
            stats["posts_collected"] = batch_stats.get("inserted", 0)
            stats["errors"].extend([f"Batch error: {e}" for e in range(batch_stats.get("errors", 0))])
        
        if comments_to_insert:
            # 댓글도 배치 처리 (유사한 방식으로 구현)
            for comment_data in comments_to_insert:
                try:
                    upsert_reddit_comment(comment_data, comment_data['post_id'], run_id)
                    stats["comments_collected"] += 1
                except Exception as e:
                    logger.error(f"Error inserting comment {comment_data['id']}: {e}")
                    stats["errors"].append(str(e))
    except Exception as e:
        logger.error(f"Batch insert error: {e}", exc_info=True)
        stats["errors"].append(str(e))
    
    logger.info(f"Processed: {stats['posts_collected']} posts, {stats['comments_collected']} comments")
    return stats
```

### 수정 3: 에러 로깅 및 재시도 메커니즘

**파일**: `worker/pipeline/db.py` (추가)

```python
import time
from functools import wraps

def retry_db_operation(max_retries=3, backoff=1.0):
    """데이터베이스 작업 재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff * (2 ** attempt)
                        logger.warning(f"DB operation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"DB operation failed after {max_retries} attempts: {e}")
                        raise
                except Exception as e:
                    # 재시도하지 않는 에러는 즉시 raise
                    raise
            raise last_exception
        return wrapper
    return decorator

@retry_db_operation(max_retries=3, backoff=1.0)
def upsert_reddit_post(post_data: Dict[str, Any], run_id: int) -> bool:
    # 기존 코드 유지하되, 재시도 로직 적용
    ...
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

# 연결 확인
assert check_database_connection(), 'DB connection failed'

# 단일 데이터셋 테스트
apify_client = ApifyClient(os.getenv('APIFY_API_TOKEN'))
run_id = create_pipeline_run('test', 'running')
stats = save_dataset(apify_client, 'Chej96NJu2xomUrg1', 'spring dinner ideas', run_id)
print(f'Test result: {stats}')
"

# 3. 배치 처리 테스트
python3 -c "
from worker.pipeline.db import upsert_reddit_posts_batch, create_pipeline_run
run_id = create_pipeline_run('test_batch', 'running')
test_posts = [{'id': 'test1', 'subreddit': 'test', 'title': 'Test', ...}]
stats = upsert_reddit_posts_batch(test_posts, run_id)
print(f'Batch test: {stats}')
"
```

### Railway 배포 후 확인

1. **Worker 로그 확인 포인트:**
   ```
   ✅ Apify 클라이언트 초기화 완료
   ✅ 데이터베이스 연결 성공
   Processing X items...
   Batch upsert: inserted=X, updated=Y, errors=Z
   ```

2. **에러 로그 확인:**
   - "too many connections" → Connection pool 문제
   - "null value in column" → 데이터 검증 문제
   - "DATABASE_URL not found" → 환경 변수 문제

3. **PostgreSQL Metrics 확인:**
   - 활성 연결 수 < 10 (정상)
   - 활성 연결 수 > 50 (문제)

4. **데이터베이스 직접 확인:**
   ```sql
   SELECT COUNT(*) FROM raw_reddit_posts;
   SELECT keyword, COUNT(*) FROM raw_reddit_posts GROUP BY keyword;
   ```

---

## 추가 수정 사항

### 환경 변수 통일

**파일**: `worker/pipeline/db.py:17-22`

```python
def get_db_connection():
    """Get database connection from DATABASE_URL"""
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    return psycopg2.connect(database_url)
```

### SSL 설정 (Railway PostgreSQL용)

```python
def get_db_connection():
    database_url = (...)
    # Railway PostgreSQL은 SSL이 필요할 수 있음
    if 'railway' in database_url.lower():
        # sslmode=require 추가 (이미 URL에 포함되어 있을 수 있음)
        if 'sslmode' not in database_url:
            database_url += '?sslmode=require'
    return psycopg2.connect(database_url)
```
