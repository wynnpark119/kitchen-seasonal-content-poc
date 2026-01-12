# DB 커넥션 풀 고갈 문제 수정 완료

## [A] 원인 결론

### 핵심 문제
1. **커넥션 반환 누락**: `conn.close()` 사용으로 풀에 반환되지 않음
2. **배치 처리 부족**: 각 임베딩마다 개별 커넥션 사용 (최대 64개 동시)
3. **API 호출 중 커넥션 점유**: 배치 내에서 개별 저장으로 여러 커넥션 필요

### 근거
- 로그: "Pool acquire timeout after 10.089s"
- 코드: `embedding.py:204-213` - 루프로 개별 `upsert_embedding` 호출
- 코드: `db.py:650` - `conn.close()` 사용 (풀 반환 안 됨)

## [B] 수정 내용

### 변경 파일 리스트
1. `worker/pipeline/db.py` - 커넥션 반환 수정 + 배치 함수 추가
2. `worker/pipeline/embedding.py` - 배치 처리로 변경

### 핵심 Diff

#### 1. 배치 upsert 함수 추가 (`db.py:611-663`)
```python
def upsert_embeddings_batch(embeddings_data: List[Tuple[...]], run_id: int):
    """한 커넥션으로 여러 임베딩 배치 저장"""
    conn = get_db_connection()
    try:
        execute_batch(cur, INSERT_SQL, insert_data, page_size=100)
        conn.commit()
    finally:
        put_db_connection(conn)  # ✅ 풀에 반환
```

#### 2. 커넥션 반환 수정 (모든 upsert 함수)
```python
# Before
finally:
    conn.close()  # ❌ 풀에 반환 안 됨

# After
finally:
    if conn:
        put_db_connection(conn)  # ✅ 풀에 반환
```

#### 3. API 호출과 DB 작업 분리 (`embedding.py:197-214`)
```python
# Before: API 호출 후 개별 저장
embeddings = generate_embeddings_batch(batch, client)
for ... in ...:
    upsert_embedding(...)  # 각각 커넥션 획득

# After: API 호출 완료 후 배치 저장
embeddings = generate_embeddings_batch(batch, client)  # API만 (커넥션 없음)
embeddings_data = [(...), ...]
upsert_embeddings_batch(embeddings_data, run_id)  # 한 커넥션으로 배치 저장
```

#### 4. 풀 크기 증가 (`db.py:103-108`)
```python
# Before
minconn=2, maxconn=10

# After
minconn=5, maxconn=20
```

#### 5. Fallback 경고 추가 (`db.py:150`)
```python
logger.warning("[DB] ⚠️ Pool exhausted, falling back to direct connection...")
```

## [C] 검증 방법

### 로컬 테스트
```bash
# 1. 임베딩 생성 실행
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."
python3 worker/run_pipeline.py --mode=analyze

# 2. 로그 확인
# - "Pool acquire timeout" 메시지 없어야 함 ✅
# - "Falling back to direct connection" 메시지 없어야 함 ✅
# - "[PROGRESS] Batch X" 메시지로 진행 상황 확인 ✅
```

### 성공 기준
- ✅ Pool acquire timeout 0회
- ✅ Fallback to direct connection 0회
- ✅ 모든 배치가 정상 처리됨
- ✅ 커넥션 풀 사용률 안정적 (maxconn=20 이하)

### 예상 결과
- 배치당 1개 커넥션만 사용 (기존: 최대 64개)
- 커넥션 풀 고갈 없음
- 처리 속도 유지 또는 개선 (배치 INSERT로 더 빠를 수 있음)

## 수정된 함수 목록

### `worker/pipeline/db.py`
- ✅ `upsert_embeddings_batch()` - 새로 추가
- ✅ `upsert_embedding()` - 커넥션 반환 수정
- ✅ `upsert_cluster_assignment()` - 커넥션 반환 수정
- ✅ `upsert_topic_qa_brief()` - 커넥션 반환 수정
- ✅ `upsert_gsc_query()` - 커넥션 반환 수정
- ✅ `check_pgvector_available()` - 커넥션 반환 수정
- ✅ `create_pipeline_run()` - 커넥션 반환 수정

### `worker/pipeline/embedding.py`
- ✅ `generate_embeddings()` - 배치 처리로 변경

## 다음 단계

1. 테스트 실행하여 풀 타임아웃 없음 확인
2. 성능 모니터링 (처리 속도, 커넥션 사용률)
3. 필요시 추가 최적화 (배치 크기 조정 등)
