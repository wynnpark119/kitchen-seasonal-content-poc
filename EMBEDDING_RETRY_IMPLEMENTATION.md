# 임베딩 재처리 시스템 구현 문서

## 개요

Reddit 데이터 적재 후 임베딩 배치 처리 중 실패한 포스트를 재처리하는 시스템을 구현했습니다.

## (A) 실패 레코드 식별 쿼리

### 스키마 근거

**파일**: `migrations/001_initial_schema.sql:125-139`

```sql
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,
    doc_id VARCHAR(100) NOT NULL,
    text_hash VARCHAR(64) NOT NULL,
    embedding_json JSONB NOT NULL,  -- NOT NULL이므로 NULL 체크 불가
    model_name VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    dim INTEGER NOT NULL DEFAULT 384,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_embeddings_doc_run UNIQUE (doc_type, doc_id, created_from_run_id),
    ...
);
```

### 실패 판단 기준

현재 스키마에서는 `embedding_json`이 `NOT NULL`이므로, **임베딩이 없는 포스트**를 실패로 간주합니다.

**실패 판단 방법**:
- **A) 특정 run_id에 대해 임베딩이 없는 포스트**: 해당 run_id에서 처리되지 않은 포스트
- **B) 모든 포스트 중 임베딩이 없는 것들**: 어떤 run_id에도 임베딩이 없는 포스트

### 실패 레코드 식별 쿼리

**파일**: `scripts/retry_failed_embeddings.py:130-201`

#### 1. 특정 run_id에 대해 실패한 포스트

```python
query = """
    SELECT DISTINCT rp.reddit_post_id, rp.title, rp.body
    FROM raw_reddit_posts rp
    WHERE NOT EXISTS (
        SELECT 1 FROM embeddings e
        WHERE e.doc_type = 'reddit_post'
        AND e.doc_id = rp.reddit_post_id
        AND e.created_from_run_id = %s
    )
    AND rp.title IS NOT NULL
    AND LENGTH(COALESCE(rp.title, '')) > 0
    ORDER BY rp.upvotes DESC, rp.num_comments DESC
"""
```

#### 2. 모든 포스트 중 임베딩이 없는 것들

```python
query = """
    SELECT DISTINCT rp.reddit_post_id, rp.title, rp.body
    FROM raw_reddit_posts rp
    WHERE NOT EXISTS (
        SELECT 1 FROM embeddings e
        WHERE e.doc_type = 'reddit_post'
        AND e.doc_id = rp.reddit_post_id
    )
    AND rp.title IS NOT NULL
    AND LENGTH(COALESCE(rp.title, '')) > 0
    ORDER BY rp.upvotes DESC, rp.num_comments DESC
"""
```

### 이미 성공한 레코드 보호

**중복 방지 메커니즘**:
1. `NOT EXISTS` 절로 이미 임베딩이 있는 포스트는 조회하지 않음
2. `upsert_embeddings_batch` 함수의 `ON CONFLICT` 절로 중복 방지:
   ```sql
   ON CONFLICT (doc_type, doc_id, created_from_run_id) DO UPDATE SET
       embedding_json = EXCLUDED.embedding_json,
       text_hash = EXCLUDED.text_hash,
       updated_at = CURRENT_TIMESTAMP
   ```
3. `text_hash` 기반 중복 체크 (선택적, 현재는 사용하지 않음)

## (B) Retry 스크립트 설계

### 파일 위치

`scripts/retry_failed_embeddings.py`

### 주요 옵션

```bash
--run-id INT          # Pipeline run ID (기본: 새로 생성)
--limit INT           # 최대 처리 개수 (기본: 500)
--since DATE          # 특정 시점 이후만 처리 (ISO: YYYY-MM-DD)
--only-status STATUS  # 상태 필터 (현재 미사용, 향후 확장용)
--dry-run             # Dry run 모드 (DB 쓰기 없음)
--batch-size INT      # Embedding API 배치 크기 (기본: 64)
--embed-concurrency INT  # Embedding API 동시 호출 수 (기본: 5)
--db-write-concurrency INT  # DB write 동시성 제한 (기본: 3)
```

### 처리 흐름

```
1. 실패한 포스트 조회 (get_failed_posts)
   ├─ 특정 run_id 또는 전체 포스트 중 임베딩 없는 것
   ├─ 댓글 조회 (상위 5개)
   └─ SERP 스니펫 조회 (선택적)

2. 안전한 embedding_text 생성 (build_safe_embedding_text)
   ├─ Title: 전체 포함
   ├─ Body: 최대 2000 토큰
   ├─ Comments: 상위 3~5개, 각 300 토큰 제한
   └─ SERP snippets: 1~2개, 각 200 토큰 제한

3. 배치 처리
   ├─ Embedding API 호출 (generate_embeddings_batch_with_retry)
   │  ├─ Permanent 에러: 즉시 실패 처리
   │  ├─ Transient 에러: 최대 3회 재시도 + exponential backoff + jitter
   │  └─ 성공한 임베딩만 반환
   └─ DB 저장 (upsert_embeddings_batch)
      ├─ Semaphore로 동시성 제한
      └─ ON CONFLICT로 중복 방지
```

### 재실행/중단/재개

- **재실행**: 같은 명령으로 다시 실행하면 idempotent하게 동작 (중복 방지)
- **중단**: Ctrl+C로 중단 가능, 이미 처리된 것은 저장됨
- **재개**: 같은 `--run-id`로 다시 실행하면 남은 것만 처리

## (C) 핵심 코드 Diff

### 1. 안전한 embedding_text 생성 함수 추가

**파일**: `worker/pipeline/preprocess.py:42-165`

```python
def build_safe_embedding_text(
    title: str,
    body: Optional[str] = None,
    comments: Optional[List[Dict[str, Any]]] = None,
    serp_snippets: Optional[List[str]] = None,
    max_tokens: int = 8192
) -> str:
    """
    안전한 embedding_text 생성 (토큰 제한 준수)
    
    정책:
    - title: 전체 포함
    - body/selftext: 토큰 기준으로 max 1500~2000
    - comments: 상위 3~5개만, 각 200~300 토큰 제한
    - serp snippet: 1~2개만, 각 150~200 토큰 제한
    """
    # tiktoken 사용 가능 여부 확인
    # 토큰 수 계산 및 우선순위 기반 구성
    # 최종 검증 및 truncate
```

**변경 사항**:
- 기존 `build_analysis_text`는 단순히 title + body 결합
- 새로운 `build_safe_embedding_text`는 토큰 제한을 준수하며 우선순위 기반 구성

### 2. 재처리 스크립트 추가

**파일**: `scripts/retry_failed_embeddings.py` (신규)

**주요 함수**:
- `get_failed_posts()`: 실패한 포스트 조회
- `is_permanent_error()`: Permanent 에러 판단
- `is_transient_error()`: Transient 에러 판단
- `generate_embeddings_batch_with_retry()`: 재시도 정책 포함 임베딩 생성
- `process_failed_embeddings()`: 메인 처리 로직

**변경 파일 리스트**:
1. `worker/pipeline/preprocess.py` - `build_safe_embedding_text` 함수 추가
2. `scripts/retry_failed_embeddings.py` - 신규 파일

### 3. 재시도 정책 구현

**파일**: `scripts/retry_failed_embeddings.py:52-95`

```python
# Permanent 에러 (재시도 금지)
PERMANENT_ERROR_CODES = {
    'invalid_request_error',
    'context_length_exceeded',
}

# Transient 에러 (재시도 허용)
TRANSIENT_ERROR_CODES = {
    'rate_limit_error',
    'server_error',
    'timeout_error',
}

def is_permanent_error(error: Exception) -> bool:
    """Permanent 에러인지 판단"""
    # 400 Bad Request, 토큰/길이 관련 에러 등

def is_transient_error(error: Exception) -> bool:
    """Transient 에러인지 판단"""
    # RateLimitError, 5xx, 네트워크 타임아웃 등
```

### 4. DB 풀 고갈 방지

**파일**: `scripts/retry_failed_embeddings.py:45-46, 291-299`

```python
# DB write 동시성 제한
db_write_semaphore = threading.Semaphore(DB_WRITE_CONCURRENCY)

# API 호출 중에는 DB 커넥션을 잡지 않음
embeddings, failed_indices = generate_embeddings_batch_with_retry(batch, client)

# DB 저장 시에만 semaphore 사용
with db_write_semaphore:
    upsert_embeddings_batch(successful_data, run_id)
```

**기존 코드와의 차이**:
- 기존 `embedding.py`는 이미 커넥션 분리 및 semaphore 적용됨
- 재처리 스크립트도 동일한 패턴 적용

## (D) 실행 예시

### 1. Dry-run (테스트)

```bash
python scripts/retry_failed_embeddings.py --dry-run --limit 10
```

**출력 예시**:
```
[INFO] Fetching failed posts (run_id=None, limit=10, since=None)...
[INFO] Found 10 failed posts to retry
[INFO] Processing 10 posts (skipped 0)
[DRY RUN] Would generate embeddings for batch of 10 posts
[INFO] Retry completed:
  Total failed: 10
  Processed: 10
  Success: 10
  Failed: 0
  Elapsed time: 0.05s
```

### 2. Limit 100 (소규모 재처리)

```bash
python scripts/retry_failed_embeddings.py --limit 100 --batch-size 32
```

**출력 예시**:
```
[INFO] Created new run_id: 123
[INFO] Fetching failed posts (run_id=123, limit=100, since=None)...
[INFO] Found 100 failed posts to retry
[INFO] Processing 95 posts (skipped 5 deleted/too short)
[PROGRESS] Batch: 32/32 success | Total: 32/95 | API: 2.3s | DB: 0.5s
[PROGRESS] Batch: 32/32 success | Total: 64/95 | API: 2.1s | DB: 0.4s
[PROGRESS] Final batch: 31/31 success | Total: 95/95 | API: 2.0s | DB: 0.4s
[INFO] Retry completed:
  Total failed: 100
  Processed: 95
  Success: 95
  Failed: 0
  Elapsed time: 15.2s
  Processing rate: 6.3 posts/s
```

### 3. 전체 재처리 (페이지네이션 포함)

```bash
# 첫 번째 배치
python scripts/retry_failed_embeddings.py --limit 500 --run-id 123

# 두 번째 배치 (이전 run_id 재사용)
python scripts/retry_failed_embeddings.py --limit 500 --run-id 123

# 또는 자동으로 계속 처리
python scripts/retry_failed_embeddings.py --limit 10000
```

### 4. 특정 시점 이후만 재처리

```bash
python scripts/retry_failed_embeddings.py --since 2025-01-01 --limit 1000
```

### 5. 기존 run_id에 대해 재처리

```bash
# 특정 run_id에 대해 실패한 것만 재처리
python scripts/retry_failed_embeddings.py --run-id 100 --limit 500
```

## (E) 성공 기준

### 검증 쿼리

#### 1. 실패 레코드 수가 0으로 수렴

```sql
-- 특정 run_id에 대해 실패한 포스트 수
SELECT COUNT(*) 
FROM raw_reddit_posts rp
WHERE NOT EXISTS (
    SELECT 1 FROM embeddings e
    WHERE e.doc_type = 'reddit_post'
    AND e.doc_id = rp.reddit_post_id
    AND e.created_from_run_id = 100  -- run_id
)
AND rp.title IS NOT NULL
AND LENGTH(COALESCE(rp.title, '')) > 0;
-- 결과: 0

-- 전체 포스트 중 임베딩이 없는 것들
SELECT COUNT(*) 
FROM raw_reddit_posts rp
WHERE NOT EXISTS (
    SELECT 1 FROM embeddings e
    WHERE e.doc_type = 'reddit_post'
    AND e.doc_id = rp.reddit_post_id
)
AND rp.title IS NOT NULL
AND LENGTH(COALESCE(rp.title, '')) > 0;
-- 결과: 0 (또는 매우 작은 수)
```

#### 2. Pool acquire timeout 0회

로그에서 다음 메시지가 없어야 함:
```
[ERROR] [DB] Pool acquire timeout after X.XXXs - pool exhausted
```

#### 3. 토큰 초과로 인한 실패는 재발하지 않음

```sql
-- 최근 생성된 임베딩 중 실패한 것 확인
SELECT COUNT(*) 
FROM embeddings e
JOIN pipeline_runs pr ON e.created_from_run_id = pr.run_id
WHERE pr.run_type = 'retry_failed_embeddings'
AND pr.status = 'failed';
-- 결과: 0 (또는 permanent 에러가 아닌 다른 원인)
```

### 성공 지표

1. ✅ **실패 레코드 수**: 0으로 수렴
2. ✅ **Pool acquire timeout**: 0회 발생
3. ✅ **토큰 초과 실패**: 재발하지 않음 (embedding_text 정책 변경 후)
4. ✅ **처리량**: 안정적인 처리 속도 (예: 5-10 posts/s)
5. ✅ **Idempotency**: 같은 명령으로 재실행해도 중복 없음

### 모니터링

```bash
# 실패한 포스트 수 확인
python -c "
from scripts.retry_failed_embeddings import get_failed_posts
posts = get_failed_posts(limit=1000)
print(f'Failed posts: {len(posts)}')
"

# 최근 run 상태 확인
python -c "
from worker.pipeline.db import get_db_connection, put_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute('SELECT run_id, run_type, status, started_at, completed_at FROM pipeline_runs WHERE run_type = %s ORDER BY started_at DESC LIMIT 5', ('retry_failed_embeddings',))
for row in cur.fetchall():
    print(row)
put_db_connection(conn)
"
```

## 추가 개선 사항

### TODO: 토큰 기반 카운팅 도입

현재는 `tiktoken`이 있으면 사용하고, 없으면 문자 길이 기반 추정을 사용합니다.

**개선 포인트**:
- `build_safe_embedding_text` 함수에서 `tiktoken` 사용을 필수로 만들기
- 또는 문자 길이 기반 추정의 정확도 개선

**위치**: `worker/pipeline/preprocess.py:42-165`

## 참고 사항

1. **민감 정보 로그 금지**: 로그에 포스트 내용이나 API 키가 노출되지 않도록 주의
2. **과도한 리팩터링 금지**: 재시도 배치 구현 및 안정장치가 최우선
3. **비용 관리**: `--limit` 옵션으로 처리량 제한 가능
4. **재실행 안전성**: `ON CONFLICT` 절로 중복 방지, idempotent 보장
