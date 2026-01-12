# Railway PostgreSQL 빠른 설정 가이드

## 현재 상태
- ❌ `DATABASE_URL` 환경 변수가 설정되지 않음
- ❌ PostgreSQL 서비스가 추가되지 않음

## 해결 방법 (3단계)

### 1단계: Railway 웹 대시보드에서 PostgreSQL 추가

**⚠️ 이 단계는 웹 대시보드에서 수동으로 해야 합니다 (CLI로 불가능)**

1. [Railway Dashboard](https://railway.app) 접속
2. 프로젝트 `kitchen-seasonal-content-poc` 선택
3. **"New"** 버튼 클릭 (왼쪽 상단 또는 중앙)
4. **"Database"** 선택
5. **"PostgreSQL"** 선택
6. PostgreSQL 서비스가 생성됨 (약 1-2분 소요)

### 2단계: DATABASE_URL 자동 설정 확인

PostgreSQL 서비스가 생성되면:
- Railway가 **자동으로** `DATABASE_URL` 환경 변수를 Streamlit 서비스에 주입합니다
- 별도 설정 불필요

확인 방법:
```bash
railway variables --service streamlit | grep DATABASE_URL
```

### 3단계: 데이터베이스 마이그레이션 실행

DATABASE_URL이 설정되면 마이그레이션 실행:

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# DATABASE_URL 확인
railway variables --service streamlit

# 마이그레이션 실행
export DATABASE_URL=$(railway variables --service streamlit | grep DATABASE_URL | awk '{print $3}')
python migrations/run_migration.py
```

또는 자동화 스크립트 사용:
```bash
./setup_railway_db.sh
```

---

## 완료 후 확인

### 1. Streamlit 서비스 재배포 확인
- Railway 대시보드에서 Streamlit 서비스 상태 확인
- 자동 재배포가 시작되면 완료 대기 (약 2-3분)

### 2. 배포 URL 접속 테스트
- URL: `https://streamlit-production-eac8.up.railway.app`
- 대시보드가 정상 로드되는지 확인

### 3. 대시보드 기능 확인
- 각 탭이 정상 작동하는지 확인
- 데이터가 없으면 "No data available" 메시지 표시 (정상)

---

## 문제 해결

### 여전히 "Application failed to respond" 에러가 발생하는 경우

1. **DATABASE_URL 확인**
   ```bash
   railway variables --service streamlit | grep DATABASE_URL
   ```

2. **로그 확인**
   ```bash
   railway logs --tail 100 --service streamlit
   ```

3. **서비스 재시작**
   - Railway 대시보드 → Streamlit 서비스 → Settings → Restart

---

## 다음 단계

PostgreSQL 설정 완료 후:
1. 데이터 수집: `python worker/run_pipeline.py --mode=collect`
2. 분석 실행: `python worker/run_pipeline.py --mode=analyze`
3. Brief 생성: `python worker/run_pipeline.py --mode=label`
4. 대시보드에서 결과 확인
