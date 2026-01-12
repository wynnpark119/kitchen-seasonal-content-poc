# DATABASE_URL 설정 완료 가이드

## ✅ 현재 상태

대시보드가 성공적으로 로드되었습니다!
- Streamlit 대시보드 정상 작동
- 6개 탭 모두 표시됨
- DATABASE_URL만 설정하면 완료

---

## 🔧 DATABASE_URL 설정 방법

### 방법 1: PostgreSQL 서비스 연결 (가장 간단) ⭐

1. Railway 대시보드 접속: https://railway.app
2. 프로젝트 선택
3. **Streamlit 서비스** 클릭
4. **"Variables"** 탭 클릭
5. **"Connect to Service"** 또는 **"Add Service"** 버튼 클릭
6. **PostgreSQL 서비스 (Postgres-tezK)** 선택
7. `DATABASE_URL`이 자동으로 추가됨

---

### 방법 2: 수동으로 DATABASE_URL 추가

1. Railway 대시보드 → Streamlit 서비스
2. **"Variables"** 탭 클릭
3. **"New Variable"** 버튼 클릭
4. 다음 정보 입력:
   - **Name**: `DATABASE_URL`
   - **Value**: `postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway`
5. **"Add"** 또는 **"Save"** 클릭

---

## ✅ 설정 완료 후

DATABASE_URL 설정 후:
- Streamlit 서비스가 자동으로 재시작됩니다
- 대시보드를 새로고침하면 데이터베이스 연결됨
- 경고 메시지가 사라지고 데이터가 표시됨

---

## 📊 확인 방법

1. **Railway 대시보드에서 확인**:
   - Streamlit 서비스 → Variables 탭
   - `DATABASE_URL`이 표시되는지 확인

2. **대시보드에서 확인**:
   - Streamlit URL: https://streamlit-production-eac8.up.railway.app
   - 새로고침 후 경고 메시지가 사라지는지 확인
   - 데이터가 표시되는지 확인 (현재는 데이터가 없을 수 있음)

---

## 🎉 완료!

DATABASE_URL 설정이 완료되면:
- ✅ 대시보드 정상 작동
- ✅ 데이터베이스 연결 완료
- ✅ 데이터 수집 및 분석 시작 가능
