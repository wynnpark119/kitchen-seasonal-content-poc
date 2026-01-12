# Streamlit 서비스에 DATABASE_URL 설정하기

## 현재 상태
- ✅ PostgreSQL 서비스 생성 완료
- ✅ DATABASE_URL 확인됨: `postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@postgres-tezk.railway.internal:5432/railway`
- ❌ Streamlit 서비스에 DATABASE_URL 미설정

## 해결 방법: Railway 웹 대시보드에서 설정

**⚠️ Railway CLI로는 환경 변수를 설정할 수 없습니다. 웹 대시보드에서만 설정 가능합니다.**

### 방법 1: PostgreSQL 서비스 연결 (권장)

1. [Railway Dashboard](https://railway.app) 접속
2. 프로젝트 `kitchen-seasonal-content-poc` 선택
3. **Streamlit 서비스** 클릭
4. **"Variables"** 탭 클릭
5. **"New Variable"** 또는 **"Connect"** 버튼 클릭
6. **PostgreSQL 서비스 (Postgres-tezK)** 선택
7. `DATABASE_URL` 환경 변수가 자동으로 추가됨

### 방법 2: 수동으로 DATABASE_URL 추가

1. **Streamlit 서비스** 클릭
2. **"Variables"** 탭 클릭
3. **"New Variable"** 버튼 클릭
4. 다음 정보 입력:
   - **Name**: `DATABASE_URL`
   - **Value**: `postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@postgres-tezk.railway.internal:5432/railway`
5. **"Add"** 또는 **"Save"** 클릭

---

## 확인 방법

설정 후 확인:
```bash
railway variables --service streamlit | grep DATABASE_URL
```

또는 Railway 대시보드에서:
- Streamlit 서비스 → Variables 탭
- `DATABASE_URL` 환경 변수 확인

---

## 다음 단계

DATABASE_URL 설정 후:

1. **Streamlit 서비스 자동 재배포**
   - Railway가 환경 변수 변경을 감지하여 자동 재배포 시작
   - 약 2-3분 소요

2. **배포 URL 접속 테스트**
   - URL: `https://streamlit-production-eac8.up.railway.app`
   - 대시보드가 정상 로드되는지 확인

3. **대시보드 기능 확인**
   - 각 탭이 정상 작동하는지 확인
   - 데이터가 없으면 "No data available" 메시지 표시 (정상)

---

## 참고

- Railway PostgreSQL의 내부 호스트명: `postgres-tezk.railway.internal`
- 외부에서 접근할 때는 다른 호스트명을 사용할 수 있습니다
- Railway는 자동으로 올바른 호스트명을 사용합니다
