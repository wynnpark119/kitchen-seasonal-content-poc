# Railway PostgreSQL 마이그레이션 실행 방법

## 방법 1: Railway CLI 사용 (권장)

### 1단계: Railway CLI 로그인 확인
```bash
railway login
```

### 2단계: 프로젝트 선택
```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
railway link  # 또는 railway init
```

### 3단계: PostgreSQL 서비스 선택
```bash
railway service
# postgres-tezk 선택
```

### 4단계: SQL 파일 실행
```bash
# 방법 A: psql 직접 실행
railway connect postgres
# 그 다음 psql에서:
\i migrations/ALL_MIGRATIONS.sql

# 방법 B: 환경 변수 설정 후 Python 스크립트 실행
railway variables --service postgres-tezk
export DATABASE_URL=$(railway variables --service postgres-tezk | grep DATABASE_URL | awk '{print $3}')
python3 migrations/run_migration.py
```

---

## 방법 2: 공개 DATABASE_URL 사용 (로컬에서 실행)

### 1단계: Railway 대시보드에서 공개 DATABASE_URL 확인

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

# Python 스크립트로 실행
python3 migrations/run_migration.py

# 또는 psql 직접 실행
psql $DATABASE_URL -f migrations/ALL_MIGRATIONS.sql
```

---

## 방법 3: 외부 클라이언트 사용 (pgAdmin, DBeaver 등)

### 1단계: Railway에서 연결 정보 확인

1. Railway 대시보드 → PostgreSQL 서비스
2. **"Connect"** 탭에서 연결 정보 확인:
   - Host (공개 호스트명)
   - Port
   - Database: `railway`
   - User: `postgres`
   - Password: (표시된 패스워드)

### 2단계: 외부 클라이언트 연결

**pgAdmin 사용:**
1. pgAdmin 실행
2. "Add New Server" 클릭
3. Railway에서 확인한 연결 정보 입력
4. 연결 후 Query Tool에서 `ALL_MIGRATIONS.sql` 실행

**DBeaver 사용:**
1. DBeaver 실행
2. "New Database Connection" → PostgreSQL 선택
3. Railway 연결 정보 입력
4. 연결 후 SQL Editor에서 `ALL_MIGRATIONS.sql` 실행

---

## 방법 4: Railway 대시보드에서 직접 실행 (가능한 경우)

Railway PostgreSQL 서비스 화면에서:
- **"Data"** 탭 → **"Query"** 버튼 (있는 경우)
- 또는 **"SQL Editor"** 탭 (있는 경우)
- 또는 **"Console"** 탭에서 psql 접근

---

## 추천 방법

**가장 간단한 방법**: 방법 2 (공개 DATABASE_URL 사용)

1. Railway 대시보드에서 공개 DATABASE_URL 확인
2. 로컬에서 `psql` 또는 Python 스크립트로 실행

---

## 확인

마이그레이션 실행 후:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

10개 테이블이 모두 보이면 성공입니다.
