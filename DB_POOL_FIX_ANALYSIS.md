# DB 커넥션 풀 고갈 문제 분석 및 수정

## [A] 원인 분석

### 문제 1: 커넥션 반환 누락
**위치**: `worker/pipeline/db.py:650`
```python
def upsert_embedding(...):
    conn = get_db_connection()  # 풀에서 가져옴
    try:
        # ... 작업 ...
    finally:
        conn.close()  # ❌ 풀에 반환하지 않고 연결을 닫아버림
```

**문제점**: `conn.close()`는 연결을 완전히 닫아버려서 풀에 반환되지 않습니다. `put_db_connection(conn)`을 사용해야 합니다.

### 문제 2: 외부 API 호출 중 DB 커넥션 점유
**위치**: `worker/pipeline/embedding.py:200-213`
```python
embeddings = generate_embeddings_batch(batch, client)  # API 호출 (수 초 소요)
# API 호출 완료 후 DB 저장 시작
for i, (post_id, text_hash, embedding) in enumerate(...):
    upsert_embedding(...)  # 각 호출마다 커넥션 획득/해제
```

**문제점**: API 호출은 완료 후에 하지만, 각 `upsert_embedding` 호출마다 개별 커넥션을 열어서 동시에 여러 커넥션이 사용됩니다.

### 문제 3: DB write 동시성 과다
**위치**: `worker/pipeline/embedding.py:204-213`
- 배치 크기 64개를 루프로 개별 저장
- 각 저장마다 커넥션 획득 → 트랜잭션 → 커밋 → 반환
- 동시에 최대 64개의 커넥션이 필요할 수 있음 (실제로는 순차이지만 빠르게 연속 호출)

**문제점**: 풀 크기(maxconn=20)보다 많은 커넥션이 필요할 수 있습니다.

### 문제 4: 배치 처리 부족
- 각 임베딩을 개별적으로 INSERT하는 대신 배치 INSERT를 사용해야 합니다.
- 현재는 64개 배치를 64번의 개별 INSERT로 처리합니다.

## [B] 수정안

### 수정 1: 커넥션 반환 수정
**파일**: `worker/pipeline/db.py`
- `upsert_embedding` 함수의 `conn.close()` → `put_db_connection(conn)` 변경
- 다른 함수들도 동일하게 수정 (`upsert_cluster_assignment`, `upsert_topic_qa_brief` 등)

### 수정 2: 배치 upsert_embedding 함수 생성
**파일**: `worker/pipeline/db.py`
- `upsert_embeddings_batch()` 함수 추가
- 한 커넥션으로 여러 임베딩을 배치 INSERT

### 수정 3: API 호출과 DB 작업 분리
**파일**: `worker/pipeline/embedding.py`
- API 호출 완료 후에만 DB 커넥션 획득
- 배치 단위로 한 번에 저장

### 수정 4: DB write 동시성 제한
**파일**: `worker/pipeline/embedding.py`
- 배치 단위로 한 번에 저장하여 동시성 문제 해결
- 필요시 semaphore 추가

### 수정 5: Fallback 경고 추가
**파일**: `worker/pipeline/db.py`
- fallback 발생 시 경고 로그 추가
- 연속 발생 시 에러로 처리

## [C] 검증 방법

### 로컬 테스트
```bash
# 1. 임베딩 생성 실행
python3 worker/run_pipeline.py --mode=analyze

# 2. 로그 확인
# - "Pool acquire timeout" 메시지 없어야 함
# - "Falling back to direct connection" 메시지 없어야 함
# - 모든 커넥션이 정상적으로 반환되어야 함
```

### 성공 기준
- ✅ Pool acquire timeout 0회
- ✅ Fallback to direct connection 0회
- ✅ 모든 배치가 정상 처리됨
- ✅ 커넥션 풀 사용률이 안정적 (maxconn 이하)
