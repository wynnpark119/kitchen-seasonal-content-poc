# 데이터베이스 마이그레이션 실행 가이드

## 문제
`postgres-tezk.railway.internal`은 Railway 내부 네트워크 호스트명이므로 로컬에서 접근할 수 없습니다.

## 해결 방법

### 방법 1: Railway 대시보드에서 공개 연결 문자열 확인

1. [Railway Dashboard](https://railway.app) 접속
2. PostgreSQL 서비스 (`Postgres-tezK`) 클릭
3. **"Connect"** 또는 **"Data"** 탭 클릭
4. **"Public Network"** 또는 **"Connection String"** 확인
5. 공개 호스트명이 포함된 DATABASE_URL 복사
   - 형식: `postgresql://postgres:패스워드@공개호스트명:포트/railway`

### 방법 2: Railway CLI로 확인

```bash
# PostgreSQL 서비스의 모든 환경 변수 확인
railway variables --service postgres-tezk

# 공개 호스트명이 포함된 DATABASE_URL 찾기
railway variables --service postgres-tezk | grep -i "public\|external\|host"
```

### 방법 3: Railway 대시보드에서 직접 마이그레이션 실행

Railway PostgreSQL 서비스의 "Query" 탭에서 직접 SQL 실행:

1. PostgreSQL 서비스 → **"Query"** 탭
2. `migrations/001_initial_schema.sql` 내용 복사하여 실행
3. `migrations/002_add_aio_status.sql` 실행
4. `migrations/003_add_insights_json.sql` 실행

---

## 마이그레이션 실행 (공개 호스트명 확인 후)

공개 호스트명을 확인하면:

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 공개 호스트명이 포함된 DATABASE_URL 설정
export DATABASE_URL="postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@공개호스트명:5432/railway"

# 마이그레이션 실행
python3 migrations/run_migration.py
```

---

## Streamlit 서비스에 DATABASE_URL 설정

### Railway 대시보드에서 설정

1. **Streamlit 서비스** 클릭
2. **"Variables"** 탭 클릭
3. **"New Variable"** 버튼 클릭
4. 다음 정보 입력:
   - **Name**: `DATABASE_URL`
   - **Value**: PostgreSQL 서비스의 DATABASE_URL (내부 호스트명 사용 가능)
     - `postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@postgres-tezk.railway.internal:5432/railway`
5. **"Add"** 또는 **"Save"** 클릭

**참고**: Streamlit 서비스는 Railway 내부 네트워크에 있으므로 `railway.internal` 호스트명을 사용할 수 있습니다.

---

## 확인 체크리스트

- [ ] PostgreSQL 서비스 생성 완료
- [ ] Streamlit 서비스에 DATABASE_URL 설정
- [ ] 마이그레이션 실행 완료
- [ ] Streamlit 서비스 재배포 확인
- [ ] 대시보드 접속 테스트

---

## 다음 단계

1. **Streamlit 서비스에 DATABASE_URL 설정** (Railway 대시보드)
2. **마이그레이션 실행** (공개 호스트명 확인 후 또는 Railway Query 탭에서)
3. **Streamlit 재배포 확인**
4. **대시보드 접속 테스트**
