# JSON Import 가이드

## 아키텍처

```
로컬 JSON 파일
    ↓
[Upload] 객체 스토리지(S3/R2/GCS) 또는 Railway Volume에 업로드
    ↓
서버 접근 가능한 위치 (s3://bucket/key.json 또는 /data/imports/file.json)
    ↓
[Import] 서버에서 실행되는 import 스크립트로 Postgres에 안정적 적재
    ↓
Postgres DB (raw_reddit_posts 테이블)
```

## 변경 파일 리스트

### 새로 생성된 파일

1. **scripts/upload_json.py**
   - 로컬 JSON 파일을 객체 스토리지(S3/R2/GCS) 또는 Railway Volume에 업로드
   - 지원: S3, Cloudflare R2, GCS, Railway Volume
   - 업로드 결과 URI 목록 생성

2. **scripts/import_json_to_db.py**
   - 서버에서 JSON 파일을 Postgres에 안정적으로 적재
   - 타임아웃, 진행률 로그, 배치 처리, 오류 격리 포함
   - Idempotent upsert (UNIQUE 키 기반)

3. **scripts/import_smoke_test.py**
   - 샘플 JSON으로 실제 upsert 검증
   - JSON 구조 검증, 데이터 준비 테스트, 배치 upsert 테스트

### 수정된 파일

1. **requirements.txt**
   - `boto3>=1.28.0` 추가 (S3/R2 지원)
   - `google-cloud-storage>=2.10.0` 추가 (GCS 지원)

2. **README.md**
   - JSON 데이터 업로드 및 적재 섹션 추가
   - Upload 단계 가이드
   - Import 단계 가이드
   - Troubleshooting 섹션 추가
   - 운영 체크리스트 추가

## 핵심 코드

### Upload 스크립트 주요 함수

```python
# S3/R2 업로드
def upload_to_s3(file_path: Path, bucket: str, key: str, 
                 access_key: str, secret_key: str, endpoint_url: Optional[str] = None) -> str

# GCS 업로드
def upload_to_gcs(file_path: Path, bucket: str, blob_name: str,
                  credentials_path: Optional[str] = None) -> str

# Railway Volume 복사
def copy_to_volume(file_path: Path, volume_path: str) -> str
```

### Import 스크립트 주요 함수

```python
# 배치 upsert (타임아웃 및 오류 격리 포함)
def batch_upsert_posts(conn, posts_data: List[tuple], batch_size: int, 
                      statement_timeout_ms: int, stats: ImportStats) -> int

# 진행률 로그
def log_progress(stats: ImportStats, progress_interval: int = 100)

# 파일 처리 (단일 JSON 파일)
def process_file(file_path: Path, keyword: str, run_id: int, batch_size: int,
                statement_timeout_ms: int, max_errors: int, stats: ImportStats, dry_run: bool) -> bool
```

### 타임아웃 설정

```python
# Connect timeout (기본값: 10초)
conn = psycopg2.connect(database_url, connect_timeout=10)

# Statement timeout (기본값: 60초 = 60000ms)
cur.execute(f"SET statement_timeout = {statement_timeout_ms}")

# Pool acquire timeout (내부: 10초)
acquire_timeout = 10.0
```

### 오류 격리

```python
# 실패한 row는 별도 리스트에 기록
stats.failed_rows.append({
    'data': row_data,
    'error': str(error)
})

# max_errors 초과 시 중단
if stats.failed_records > max_errors:
    logger.error(f"Too many errors, stopping")
    break
```

## 실행 예시

### 1. 로컬 업로드 (S3)

```bash
# 환경 변수 설정
export STORAGE_PROVIDER=s3
export STORAGE_BUCKET=my-bucket
export STORAGE_ACCESS_KEY=your-access-key
export STORAGE_SECRET_KEY=your-secret-key

# 업로드
python scripts/upload_json.py \
    --input data/collection.json \
    --provider s3 \
    --bucket my-bucket \
    --prefix imports/2024-01-15

# 결과: uploaded_uris_import-20240115-123456-abc12345.txt 생성
```

### 2. 서버 Import (Railway)

```bash
# Railway CLI로 실행
railway run python scripts/import_json_to_db.py \
    --input-uris uploaded_uris_import-20240115-123456-abc12345.txt \
    --batch-size 500 \
    --max-errors 1000 \
    --job-id import-20240115-123456

# 또는 단일 파일 직접 지정
railway run python scripts/import_json_to_db.py \
    --input s3://my-bucket/imports/2024-01-15/collection.json \
    --batch-size 500
```

### 3. 검증

```bash
# DB 연결 테스트
python scripts/db_smoke_test.py

# Import 검증 (샘플 데이터)
python scripts/import_smoke_test.py \
    --input data/collection.json \
    --sample-size 10

# Dry run (DB 쓰기 없이 테스트)
python scripts/import_json_to_db.py \
    --input data/collection.json \
    --dry-run
```

## 운영 체크리스트

### 시작 로그 확인

```
✅ Job ID: import-20240115-123456-abc12345
✅ Database: ...@xxx.railway.app
✅ Files: 5
✅ Batch size: 500
✅ Statement timeout: 60000ms
```

### 진행 중 로그 확인

```
✅ [PROGRESS] Records: 1000/5000 (Success: 1000, Failed: 0) | Elapsed: 95.2s | Rate: 10.5 records/s
✅ ✅ Successfully inserted 500 posts
```

### 종료 로그 확인

```
✅ Total records: 5000
✅ Success: 4950
✅ Failed: 50
✅ Average rate: 10.2 records/s
✅ Failed rows (showing up to 10): [실패 샘플]
```

### 경고 신호

- ⚠️ `Pool acquire timeout` → 연결 풀 부족
- ⚠️ `Query timeout` → 쿼리 타임아웃
- ⚠️ `Too many errors (1001 > 1000), stopping` → max_errors 초과
- ⚠️ 진행률 로그가 30초 이상 갱신되지 않음 → Hang 가능성

## 환경 변수 요약

### Upload 단계 (로컬)

- `STORAGE_PROVIDER`: s3|r2|gcs|volume
- `STORAGE_BUCKET`: 버킷 이름
- `STORAGE_PREFIX`: 키 prefix
- `STORAGE_ACCESS_KEY`: Access Key ID
- `STORAGE_SECRET_KEY`: Secret Access Key
- `STORAGE_ENDPOINT_URL`: R2용 endpoint URL
- `IMPORT_DIR`: Railway Volume 경로

### Import 단계 (서버)

- `DATABASE_URL`: PostgreSQL 연결 문자열 (Railway에서 자동 주입)
- `STORAGE_ACCESS_KEY`: S3/R2 다운로드용 (선택)
- `STORAGE_SECRET_KEY`: S3/R2 다운로드용 (선택)
- `STORAGE_ENDPOINT_URL`: R2 다운로드용 (선택)
- `GOOGLE_APPLICATION_CREDENTIALS`: GCS 다운로드용 (선택)

## Railway 서비스별 역할 분리

### Web 서비스 (Streamlit)

- 역할: 대시보드 표시
- 환경 변수: `DATABASE_URL` (읽기 전용)
- 시작 명령: `bash start_streamlit.sh`

### Worker 서비스

- 역할: 데이터 수집/분석 파이프라인
- 환경 변수: `DATABASE_URL`, API keys 등
- 시작 명령: `python -m worker.main`

### Import 실행 방법

**방법 A: One-off 실행 (권장)**
- Railway CLI: `railway run python scripts/import_json_to_db.py ...`
- 배포 후 수동 실행 가능
- 별도 서비스 불필요

**방법 B: Worker 서비스로 실행**
- `railway-worker.json`의 start command를 임시로 변경
- 또는 별도의 import worker 서비스 생성
- 환경 변수로 파일 위치 주입

**권장**: 방법 A (One-off 실행)를 사용하여 web/worker와 import의 역할을 명확히 분리
