# Railway PostgreSQL 데이터베이스 설정 가이드

## 문제
"Application failed to respond" 에러가 발생하는 이유는 `DATABASE_URL` 환경 변수가 설정되지 않았기 때문입니다.

## 해결 방법

### 1. Railway에서 PostgreSQL 서비스 추가

1. [Railway Dashboard](https://railway.app) 접속
2. 프로젝트 `kitchen-seasonal-content-poc` 선택
3. "New" 버튼 클릭
4. "Database" 선택
5. "PostgreSQL" 선택
6. PostgreSQL 서비스가 생성됨

### 2. Streamlit 서비스에 PostgreSQL 연결

#### 방법 1: 자동 연결 (권장)
- Railway가 자동으로 `DATABASE_URL` 환경 변수를 Streamlit 서비스에 주입합니다
- 별도 설정 불필요

#### 방법 2: 수동 연결
1. Streamlit 서비스 선택
2. "Variables" 탭 클릭
3. PostgreSQL 서비스의 "Connect" 버튼 클릭
4. `DATABASE_URL` 환경 변수가 자동으로 추가됨

### 3. 환경 변수 확인

```bash
railway variables --service streamlit
```

다음과 같은 변수가 있어야 합니다:
- `DATABASE_URL` (PostgreSQL 연결 문자열)

### 4. 데이터베이스 마이그레이션 실행

PostgreSQL 서비스가 생성되면, 마이그레이션을 실행해야 합니다:

#### 방법 1: Railway CLI로 실행
```bash
# PostgreSQL 서비스에 연결
railway connect postgres

# 마이그레이션 실행
psql $DATABASE_URL -f migrations/001_initial_schema.sql
psql $DATABASE_URL -f migrations/002_add_aio_status.sql
psql $DATABASE_URL -f migrations/003_add_insights_json.sql
```

#### 방법 2: 로컬에서 실행
```bash
# DATABASE_URL 환경 변수 설정
export DATABASE_URL="postgresql://postgres:password@host:port/railway"

# 마이그레이션 실행
python migrations/run_migration.py
```

### 5. 재배포 확인

1. Railway 대시보드에서 Streamlit 서비스 확인
2. "Deployments" 탭에서 최신 배포 상태 확인
3. 배포 URL 접속 테스트

---

## 확인 체크리스트

- [ ] PostgreSQL 서비스 생성됨
- [ ] `DATABASE_URL` 환경 변수 설정됨
- [ ] 데이터베이스 마이그레이션 실행됨
- [ ] Streamlit 서비스 재배포됨
- [ ] 배포 URL 접속 성공
- [ ] 대시보드 정상 작동

---

## 예상되는 결과

### DATABASE_URL이 설정된 경우
- 대시보드가 정상 로드됨
- 각 탭에서 데이터 조회 가능 (데이터가 있으면)
- "No data available" 메시지 표시 (데이터가 없으면)

### DATABASE_URL이 없는 경우
- 대시보드가 로드되지만 에러 메시지 표시
- PostgreSQL 설정 안내 메시지 표시

---

## 문제 해결

### 여전히 "Application failed to respond" 에러가 발생하는 경우

1. **로그 확인**
   ```bash
   railway logs --tail 100 --service streamlit
   ```

2. **환경 변수 재확인**
   ```bash
   railway variables --service streamlit
   ```

3. **서비스 재시작**
   - Railway 대시보드에서 Streamlit 서비스 선택
   - "Settings" → "Restart" 클릭

4. **재배포**
   - Railway 대시보드에서 "Redeploy" 클릭
