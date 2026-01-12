# Railway 마이그레이션 실행 가이드

## 방법 1: Python 스크립트 사용 (가장 간단)

### 1단계: Railway에서 공개 DATABASE_URL 확인

1. Railway 대시보드 → PostgreSQL 서비스 (`Postgres-tezK`)
2. **"Connect"** 또는 **"Data"** 탭 클릭
3. **"Public Network"** 또는 **"Connection String"** 확인
4. 공개 호스트명이 포함된 DATABASE_URL 복사
   - 형식: `postgresql://postgres:패스워드@공개호스트명:포트/railway`
   - 예: `postgresql://postgres:password@xxxx.proxy.rlwy.net:5432/railway`

### 2단계: 로컬에서 마이그레이션 실행

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 공개 DATABASE_URL 설정
export DATABASE_URL="postgresql://postgres:패스워드@공개호스트명:포트/railway"

# 마이그레이션 실행
python3 migrations/run_migration.py
```

---

## 방법 2: psql 직접 사용

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 공개 DATABASE_URL 설정
export DATABASE_URL="postgresql://postgres:패스워드@공개호스트명:포트/railway"

# psql로 직접 실행
psql $DATABASE_URL -f migrations/ALL_MIGRATIONS.sql
```

---

## 방법 3: Railway CLI 사용

```bash
# Railway CLI 로그인 확인
railway login

# 프로젝트 디렉토리에서
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
railway link

# PostgreSQL 서비스 선택
railway service
# postgres-tezk 선택

# DATABASE_URL 자동 설정 후 실행
python3 migrations/run_migration.py
```

---

## 확인

마이그레이션 실행 후, 다음 쿼리로 확인:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

예상 결과: 10개 테이블
- pipeline_runs
- raw_reddit_posts
- raw_reddit_comments
- raw_serp_aio
- raw_gsc_queries
- embeddings
- clusters
- cluster_assignments
- cluster_timeseries
- topic_qa_briefs

---

## 문제 해결

### psycopg2가 설치되지 않은 경우
```bash
pip install psycopg2-binary
```

### psql이 설치되지 않은 경우
- macOS: `brew install postgresql`
- 또는 방법 1 (Python 스크립트) 사용

### 연결 실패하는 경우
- Railway 대시보드에서 **공개 호스트명**을 사용하는지 확인
- 내부 호스트명 (`railway.internal`)은 로컬에서 접근 불가
