# DATABASE_URL 확인 및 설정 가이드

## Railway PostgreSQL DATABASE_URL 형식

Railway에서 PostgreSQL 서비스를 생성하면 자동으로 생성되는 DATABASE_URL 형식:

```
postgresql://postgres:PASSWORD@HOST:PORT/railway
```

**패스워드는 반드시 포함되어 있습니다!** Railway가 자동으로 생성합니다.

---

## DATABASE_URL 확인 방법

### 방법 1: Railway 웹 대시보드에서 확인

1. [Railway Dashboard](https://railway.app) 접속
2. 프로젝트 선택
3. **PostgreSQL 서비스 (Postgres-tezK)** 클릭
4. **"Variables"** 탭 클릭
5. `DATABASE_URL` 또는 `POSTGRES_URL` 확인
   - 형식: `postgresql://postgres:랜덤패스워드@호스트:포트/railway`

### 방법 2: Railway CLI로 확인

```bash
# PostgreSQL 서비스의 DATABASE_URL 확인
railway variables --service postgres-tezk

# 또는 프로젝트 전체 환경 변수 확인
railway variables
```

---

## Streamlit 서비스에 DATABASE_URL 연결

### 방법 1: Railway 웹 대시보드에서 연결 (권장)

1. **Streamlit 서비스** 클릭
2. **"Variables"** 탭 클릭
3. **"New Variable"** 또는 **"Connect"** 버튼 클릭
4. **PostgreSQL 서비스 (Postgres-tezK)** 선택
5. `DATABASE_URL` 환경 변수가 자동으로 추가됨

### 방법 2: 수동으로 DATABASE_URL 설정

PostgreSQL 서비스의 DATABASE_URL을 복사하여 Streamlit 서비스에 설정:

1. PostgreSQL 서비스 → Variables → `DATABASE_URL` 복사
2. Streamlit 서비스 → Variables → "New Variable"
3. Name: `DATABASE_URL`
4. Value: 복사한 DATABASE_URL 붙여넣기
5. Save

---

## DATABASE_URL 형식 예시

Railway PostgreSQL의 실제 DATABASE_URL 예시:

```
postgresql://postgres:AbCdEf123456@containers-us-west-123.railway.app:5432/railway
```

구성 요소:
- `postgres` - 사용자명 (기본값)
- `AbCdEf123456` - Railway가 자동 생성한 패스워드
- `containers-us-west-123.railway.app` - 호스트
- `5432` - 포트
- `railway` - 데이터베이스명

---

## 문제 해결

### DATABASE_URL에 패스워드가 없는 경우

이는 정상적이지 않습니다. Railway PostgreSQL은 항상 패스워드를 포함합니다.

확인 사항:
1. PostgreSQL 서비스가 정상적으로 생성되었는지 확인
2. Variables 탭에서 `DATABASE_URL` 또는 `POSTGRES_URL` 확인
3. 서비스가 아직 초기화 중일 수 있음 (몇 분 대기)

### DATABASE_URL이 Streamlit 서비스에 없는 경우

1. Railway 대시보드에서 Streamlit 서비스 선택
2. Variables 탭에서 PostgreSQL 서비스 연결
3. 또는 수동으로 DATABASE_URL 추가

---

## 다음 단계

DATABASE_URL이 설정되면:

1. **확인**
   ```bash
   railway variables --service streamlit | grep DATABASE_URL
   ```

2. **마이그레이션 실행**
   ```bash
   export DATABASE_URL=$(railway variables --service streamlit | grep DATABASE_URL | awk '{print $3}')
   python migrations/run_migration.py
   ```

3. **Streamlit 재배포 확인**
   - Railway 대시보드에서 자동 재배포 확인
   - 배포 URL 접속 테스트
