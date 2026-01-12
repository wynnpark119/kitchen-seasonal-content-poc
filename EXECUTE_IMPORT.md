# JSON Import 실행 가이드

## 현재 상태

✅ **확인 완료:**
- `data/` 디렉토리에 20개의 JSON 파일 존재
- 파일 크기: 약 1-1.6MB (각 파일)

## 실행 단계

### 1단계: 로컬 환경 준비

```bash
# 프로젝트 디렉토리로 이동
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 의존성 설치
pip install -r requirements.txt
# 또는
pip3 install -r requirements.txt

# 환경 변수 확인 (DATABASE_URL이 설정되어 있어야 함)
# Railway에서 DATABASE_URL을 가져오거나 .env 파일에 설정
```

### 2단계: 검증 (로컬)

```bash
# DB 연결 테스트
python3 scripts/db_smoke_test.py

# Import 검증 (Dry run)
python3 scripts/import_smoke_test.py \
    --input data/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --sample-size 10 \
    --dry-run
```

### 3단계: 업로드 (로컬에서 실행)

#### 옵션 A: S3/R2 업로드 (권장)

```bash
# 환경 변수 설정
export STORAGE_PROVIDER=s3  # 또는 r2
export STORAGE_BUCKET=your-bucket-name
export STORAGE_ACCESS_KEY=your-access-key
export STORAGE_SECRET_KEY=your-secret-key
export STORAGE_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com  # R2만 필요

# 단일 파일 업로드
python3 scripts/upload_json.py \
    --input data/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --provider s3 \
    --bucket your-bucket-name \
    --prefix imports/2024-01-15

# 또는 전체 디렉토리 업로드
python3 scripts/upload_json.py \
    --input data/ \
    --provider s3 \
    --bucket your-bucket-name \
    --prefix imports/2024-01-15
```

#### 옵션 B: Railway Volume 사용

```bash
# Railway CLI로 파일 복사
railway run cp data/spring_dinner_ideas_Chej96NJu2xomUrg1.json /data/imports/
```

### 4단계: 서버에서 Import 실행

#### 방법 A: Railway One-off 실행 (권장)

```bash
# 업로드 결과 URI 목록 파일이 있는 경우
railway run python3 scripts/import_json_to_db.py \
    --input-uris uploaded_uris_import-20240115-123456-abc12345.txt \
    --batch-size 500 \
    --max-errors 1000

# 또는 S3 URI 직접 지정
railway run python3 scripts/import_json_to_db.py \
    --input s3://your-bucket/imports/2024-01-15/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --batch-size 500

# 또는 Railway Volume 경로 지정
railway run python3 scripts/import_json_to_db.py \
    --input /data/imports/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --batch-size 500
```

#### 방법 B: 로컬에서 직접 Import (DATABASE_URL 설정 필요)

```bash
# 환경 변수 설정
export DATABASE_URL="postgresql://user:password@host:port/dbname?sslmode=require"

# Import 실행
python3 scripts/import_json_to_db.py \
    --input data/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --batch-size 500 \
    --max-errors 1000
```

## 빠른 실행 예시

### 시나리오 1: 로컬에서 직접 Import (Railway DB 사용)

```bash
# 1. Railway에서 DATABASE_URL 가져오기
railway variables

# 2. 환경 변수 설정
export DATABASE_URL="<Railway에서 복사한 DATABASE_URL>"

# 3. Import 실행
python3 scripts/import_json_to_db.py \
    --input data/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --batch-size 500
```

### 시나리오 2: S3 업로드 후 Railway에서 Import

```bash
# 1. 로컬에서 업로드
python3 scripts/upload_json.py \
    --input data/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --provider s3 \
    --bucket your-bucket \
    --prefix imports/2024-01-15

# 2. 생성된 URI 목록 파일 확인
cat uploaded_uris_*.txt

# 3. Railway에서 Import
railway run python3 scripts/import_json_to_db.py \
    --input-uris uploaded_uris_*.txt \
    --batch-size 500
```

## 현재 사용 가능한 JSON 파일 목록

```
data/spring_dinner_ideas_Chej96NJu2xomUrg1.json (약 1.6MB)
data/easy_spring_meals_hYNaDehMRGFbLd9sW.json (약 1.0MB)
data/fridge_organization_system_s9N4ldadvFkUSC2Yr.json (약 1.6MB)
data/fridge_organization_tips_MZUpZW7AsSGmM7Pme.json (약 1.4MB)
... (총 20개 파일)
```

## 다음 단계

1. **의존성 설치 확인**: `pip3 install -r requirements.txt`
2. **DATABASE_URL 설정**: Railway에서 가져오거나 .env 파일에 설정
3. **검증 실행**: `python3 scripts/db_smoke_test.py`
4. **Import 실행**: 위의 시나리오 중 하나 선택하여 실행

## 문제 해결

### 의존성 오류
```bash
pip3 install -r requirements.txt
```

### DATABASE_URL 오류
- Railway 대시보드에서 `DATABASE_URL` 확인
- 또는 `.env` 파일에 설정

### 권한 오류
- `.env` 파일 읽기 권한 확인
- 또는 환경 변수로 직접 설정
