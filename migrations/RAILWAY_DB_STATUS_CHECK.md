# Railway 데이터베이스 상태 확인 가이드

## 현재 상황
Railway에 이미 데이터베이스가 생성되어 있습니다. 스키마와 데이터 상태를 확인해야 합니다.

---

## 확인 방법

### 1단계: Railway Query 탭에서 상태 확인

1. Railway 대시보드 → PostgreSQL 서비스 (`Postgres-tezK`) → **Query** 탭
2. `migrations/CHECK_RAILWAY_DB_STATUS.sql` 파일 내용 복사
3. Query 탭에 붙여넣기 후 **Run** 클릭

### 확인 항목

#### A) 테이블 목록 확인
- 10개 테이블이 모두 있는지 확인:
  - `pipeline_runs`
  - `raw_reddit_posts`
  - `raw_reddit_comments`
  - `raw_serp_aio`
  - `raw_gsc_queries`
  - `embeddings`
  - `clusters`
  - `cluster_assignments`
  - `cluster_timeseries`
  - `topic_qa_briefs`

#### B) 데이터 개수 확인
- 각 테이블에 데이터가 있는지 확인
- `row_count`가 0이면 빈 테이블, 0보다 크면 데이터 존재

#### C) 마이그레이션 필요 여부 확인
- `raw_serp_aio` 테이블에 `aio_status` 컬럼이 있는지
- `topic_qa_briefs` 테이블에 `insights_json` 컬럼이 있는지

---

## 시나리오별 대응

### 시나리오 1: 테이블이 없음 (빈 DB)
→ `migrations/ALL_MIGRATIONS.sql` 전체 실행

### 시나리오 2: 테이블은 있지만 일부 컬럼 누락
→ 누락된 마이그레이션만 실행:
- `aio_status` 없으면 → `002_add_aio_status.sql` 실행
- `insights_json` 없으면 → `003_add_insights_json.sql` 실행

### 시나리오 3: 모든 테이블과 컬럼이 이미 있음
→ 마이그레이션 불필요, 바로 사용 가능

### 시나리오 4: 테이블은 있지만 데이터가 없음
→ 스키마는 완료, 데이터 수집만 진행하면 됨

---

## 다음 단계

상태 확인 후 결과를 알려주시면:
1. 필요한 마이그레이션만 실행하거나
2. 바로 데이터 수집/분석을 진행할 수 있습니다
