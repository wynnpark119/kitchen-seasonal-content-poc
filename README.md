# kitchen-seasonal-content-poc

Reddit / Google SERP / GSC 데이터를 분석하는 파이프라인과 Streamlit 대시보드를 개발하는 PoC 프로젝트입니다.

## 기술 스택

- Python 3.11
- Streamlit (대시보드)
- PostgreSQL (데이터베이스)
- Railway (배포 플랫폼)
- Docker (컨테이너화)

## 개발 가이드

이 프로젝트는 PoC이며, **SPEC.md**와 **TASKS.md**를 기준으로 개발합니다.

## 프로젝트 구조

```
kitchen-seasonal-content-poc/
├── web/            # Streamlit 대시보드
├── worker/         # 데이터 수집/분석 파이프라인
├── common/         # DB, 설정, 공용 유틸
├── data/           # 임시 CSV, 중간 산출물 (gitignore 대상)
├── tests/          # 최소 테스트/검증 스크립트
├── migrations/     # DB DDL / 마이그레이션 SQL
├── Dockerfile      # Streamlit 서비스용
├── worker/Dockerfile  # Worker 서비스용
├── requirements.txt
├── railway.json    # Railway Streamlit 서비스 설정
├── railway-worker.json  # Railway Worker 서비스 설정
├── .env.example
└── README.md
```

## Railway 배포

### 1. Railway 프로젝트 생성

1. [Railway](https://railway.app)에 로그인
2. "New Project" 생성
3. GitHub 저장소 연결

### 2. PostgreSQL 데이터베이스 추가

1. Railway 프로젝트에서 "New" → "Database" → "PostgreSQL" 선택
2. 데이터베이스가 생성되면 `DATABASE_URL` 환경 변수가 자동으로 설정됩니다

### 3. Streamlit 서비스 배포

1. "New" → "GitHub Repo" 선택
2. 저장소 선택 후 배포
3. Railway가 `Dockerfile`을 자동 감지하여 빌드
4. 환경 변수 설정:
   - `PORT=8501` (자동 설정됨)
   - `DATABASE_URL` (PostgreSQL 플러그인에서 자동 주입)

### 4. Worker 서비스 배포 (선택사항)

1. 동일한 프로젝트에서 "New" → "GitHub Repo" 선택
2. 같은 저장소 선택
3. Railway 설정에서:
   - Dockerfile 경로: `worker/Dockerfile`
   - 시작 명령: `python -m worker.main`
   - 또는 `railway-worker.json` 사용

### 5. 환경 변수 설정

Railway 대시보드에서 각 서비스의 "Variables" 탭에서 환경 변수 설정:
- `.env.example` 파일 참고

## 로컬 개발

### 1. 가상환경 설정

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 값 입력
```

### 4. Streamlit 실행

```bash
streamlit run web/app.py
```

### 5. Worker 실행

```bash
# 전체 파이프라인 실행
python worker/run_pipeline.py --mode=all

# 개별 모드 실행
python worker/run_pipeline.py --mode=collect          # Reddit + SERP AIO 수집
python worker/run_pipeline.py --mode=ingest_gsc --gsc-csv data/gsc_data.csv  # GSC CSV 업로드
python worker/run_pipeline.py --mode=analyze          # 정제/임베딩/클러스터링
python worker/run_pipeline.py --mode=label            # LLM 기반 brief 생성

# Dry run (DB 쓰기 없이 테스트)
python worker/run_pipeline.py --mode=all --dry-run
```

## JSON 데이터 업로드 및 적재

로컬에 수집된 JSON 데이터를 서버에 업로드한 후 Postgres에 안정적으로 적재하는 방법입니다.

### 아키텍처

```
로컬 JSON 파일
    ↓
[1] Upload 단계: 객체 스토리지(S3/R2/GCS) 또는 Railway Volume에 업로드
    ↓
서버 접근 가능한 위치 (s3://bucket/key.json 또는 /data/imports/file.json)
    ↓
[2] Import 단계: 서버에서 실행되는 import 스크립트로 Postgres에 적재
    ↓
Postgres DB (raw_reddit_posts 테이블)
```

### 1. Upload 단계 (로컬에서 실행)

#### S3/R2 업로드 (권장)

```bash
# 환경 변수 설정
export STORAGE_PROVIDER=s3  # 또는 r2
export STORAGE_BUCKET=my-bucket
export STORAGE_PREFIX=imports/2024-01-15
export STORAGE_ACCESS_KEY=your-access-key
export STORAGE_SECRET_KEY=your-secret-key
export STORAGE_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com  # R2만 필요

# 단일 파일 업로드
python scripts/upload_json.py \
    --input data/collection.json \
    --provider s3 \
    --bucket my-bucket \
    --prefix imports/2024-01-15

# 디렉토리 업로드
python scripts/upload_json.py \
    --input data/ \
    --provider s3 \
    --bucket my-bucket \
    --prefix imports/2024-01-15
```

#### GCS 업로드

```bash
# 환경 변수 설정
export STORAGE_PROVIDER=gcs
export STORAGE_BUCKET=my-bucket
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# 업로드
python scripts/upload_json.py \
    --input data/collection.json \
    --provider gcs \
    --bucket my-bucket \
    --prefix imports/2024-01-15
```

#### Railway Volume 복사 (대안)

```bash
# Railway CLI를 통한 복사 (로컬 → 서버)
railway run cp data/collection.json /data/imports/

# 또는 서버에서 직접 실행하는 경우
python scripts/upload_json.py \
    --input data/collection.json \
    --provider volume \
    --volume-path /data/imports
```

**업로드 결과**: `uploaded_uris_<job-id>.txt` 파일이 생성되며, 서버에서 import 시 사용할 URI 목록이 저장됩니다.

### 2. Import 단계 (서버에서 실행)

#### Railway에서 실행

**방법 A: One-off 실행 (권장)**

```bash
# Railway CLI로 서버에서 직접 실행
railway run python scripts/import_json_to_db.py \
    --input-uris uploaded_uris_job123.txt \
    --batch-size 500 \
    --max-errors 1000

# 또는 단일 파일/디렉토리 직접 지정
railway run python scripts/import_json_to_db.py \
    --input s3://bucket/key.json \
    --batch-size 500
```

**방법 B: Worker 서비스로 실행**

`railway-worker.json`의 start command를 임시로 변경하거나, 별도의 import worker 서비스를 생성:

```json
{
  "deploy": {
    "startCommand": "python scripts/import_json_to_db.py --input-uris $IMPORT_URIS_FILE --batch-size 500"
  }
}
```

환경 변수 설정:
- `IMPORT_URIS_FILE`: 업로드된 URI 목록 파일 경로
- `DATABASE_URL`: PostgreSQL 연결 문자열 (자동 주입됨)

#### Import 스크립트 옵션

```bash
python scripts/import_json_to_db.py \
    --input <file-or-dir> \              # 입력 파일/디렉토리
    --input-uris <uri-list-file> \      # 또는 URI 목록 파일
    --batch-size 500 \                  # 배치 크기 (기본값: 500)
    --max-errors 1000 \                 # 최대 오류 수 (기본값: 1000)
    --job-id custom-job-123 \          # Job ID (기본값: 자동 생성)
    --keyword "spring recipes" \       # 키워드 (기본값: 파일명에서 추출)
    --connect-timeout 10 \             # 연결 타임아웃 (초)
    --statement-timeout 60000 \        # 쿼리 타임아웃 (밀리초)
    --dry-run                          # Dry run 모드 (DB 쓰기 없음)
```

#### 필수 환경 변수

**서버 측 (Railway)**:
- `DATABASE_URL`: PostgreSQL 연결 문자열 (Railway에서 자동 주입)

**객체 스토리지에서 다운로드하는 경우**:
- `STORAGE_ACCESS_KEY`: Access Key ID
- `STORAGE_SECRET_KEY`: Secret Access Key
- `STORAGE_ENDPOINT_URL`: R2용 endpoint URL (선택)

### 3. 검증 스크립트

#### DB 연결 테스트

```bash
python scripts/db_smoke_test.py
```

#### Import 검증 (샘플 데이터)

```bash
# 기본 (data/ 디렉토리의 첫 번째 JSON 파일 사용, 10개 샘플)
python scripts/import_smoke_test.py

# 특정 파일 지정
python scripts/import_smoke_test.py \
    --input data/collection.json \
    --sample-size 10

# Dry run
python scripts/import_smoke_test.py --dry-run
```

## Troubleshooting

### DB 적재 시 Hang 발생

#### 1. 타임아웃 로그 확인

Import 스크립트는 다음 타임아웃을 설정합니다:
- **Connect timeout**: 10초 (기본값)
- **Statement timeout**: 60초 (기본값, `--statement-timeout`로 변경 가능)
- **Pool acquire timeout**: 10초 (내부)

로그에서 다음 메시지를 확인:
```
[DB] Pool acquire timeout after 10.000s - pool may be exhausted
[DB] Query timeout (statement_timeout exceeded)
```

**해결 방법**:
- `--statement-timeout` 값을 증가 (예: `--statement-timeout 120000` = 120초)
- `--batch-size` 값을 감소 (예: `--batch-size 100`)
- DB 연결 풀 확인 (동시 실행 중인 다른 프로세스 확인)

#### 2. DB 락 확인

```sql
-- 활성 쿼리 확인
SELECT pid, usename, application_name, state, query, query_start
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;

-- 락 대기 확인
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query,
       blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

**해결 방법**:
- 오래 실행 중인 쿼리 종료: `SELECT pg_terminate_backend(pid);`
- Import 스크립트를 단일 인스턴스로만 실행

#### 3. DATABASE_URL 확인

```bash
# Railway에서 확인
railway variables

# 또는 서버에서 확인 (마스킹된 형태)
python scripts/db_smoke_test.py
```

**문제점**:
- `DATABASE_URL`이 설정되지 않음
- 잘못된 연결 문자열
- SSL 설정 누락 (Railway는 `sslmode=require` 필요)

**해결 방법**:
- Railway 대시보드에서 `DATABASE_URL` 확인
- `scripts/db_smoke_test.py`로 연결 테스트

#### 4. 진행률 로그 확인

Import 스크립트는 100건마다 또는 10초마다 진행률을 로깅합니다:

```
[PROGRESS] Records: 500/1000 (Success: 500, Failed: 0) | Elapsed: 45.2s | Rate: 11.1 records/s
```

**멈춤 감지**:
- 진행률 로그가 30초 이상 갱신되지 않음 → 타임아웃 또는 락 가능성
- `Failed` 수가 급격히 증가 → 데이터 문제 또는 DB 제약 조건 위반

#### 5. 실패 row 확인

Import 실패 시 `failed_rows_<job-id>.json` 파일이 생성됩니다:

```bash
# 실패 row 확인
cat failed_rows_job123.json

# 실패 원인 분석
python -c "import json; data=json.load(open('failed_rows_job123.json')); print('\n'.join([f\"{r['data'].get('post_id', 'unknown')}: {r['error']}\" for r in data[:10]]))"
```

**일반적인 실패 원인**:
- 중복 키 (이미 존재하는 `reddit_post_id`) → 정상 (upsert로 처리됨)
- NULL 제약 조건 위반 → 데이터 검증 필요
- 타입 불일치 → JSON 구조 확인 필요

### 운영 체크리스트

Import 실행 시 로그에서 확인해야 할 지표:

#### 시작 로그
- ✅ `Job ID: import-20240115-123456-abc12345`
- ✅ `Database: ...@xxx.railway.app` (마스킹된 URL)
- ✅ `Files: 5` (처리할 파일 수)
- ✅ `Batch size: 500`

#### 진행 중 로그
- ✅ `[PROGRESS] Records: 1000/5000` (정기적으로 갱신)
- ✅ `Rate: 10.5 records/s` (처리 속도)
- ✅ `✅ Successfully inserted 500 posts` (배치 성공)

#### 종료 로그
- ✅ `Total records: 5000`
- ✅ `Success: 4950`
- ✅ `Failed: 50` (0이면 완벽)
- ✅ `Average rate: 10.2 records/s`
- ✅ `Failed rows (showing up to 10):` (실패 샘플)

#### 경고 신호
- ⚠️ `Pool acquire timeout` → 연결 풀 부족
- ⚠️ `Query timeout` → 쿼리가 너무 오래 실행
- ⚠️ `Too many errors (1001 > 1000), stopping` → max_errors 초과
- ⚠️ 진행률 로그가 30초 이상 갱신되지 않음 → Hang 가능성

## 주의사항

- `.env` 파일은 절대 커밋하지 마세요 (`.gitignore`에 포함됨)
- `data/` 폴더는 로컬 개발용이며 커밋되지 않습니다
- Railway에서 PostgreSQL 플러그인 사용 시 `DATABASE_URL`이 자동으로 주입됩니다
- Import 스크립트는 idempotent하게 동작합니다 (같은 데이터를 여러 번 실행해도 안전)
- 실패한 row는 별도 파일로 저장되며, 전체 프로세스가 중단되지 않습니다
