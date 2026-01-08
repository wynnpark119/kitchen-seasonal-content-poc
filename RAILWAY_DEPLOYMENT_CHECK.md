# Railway 배포 상태 확인 가이드

## 방법 1: Railway 웹 대시보드에서 확인 (권장)

### 1. Railway 대시보드 접속
1. [Railway Dashboard](https://railway.app)에 로그인
2. 프로젝트 선택: `kitchen-seasonal-content-poc`

### 2. 서비스 상태 확인

#### Web 서비스 (Streamlit)
- 서비스 목록에서 "streamlit" 또는 "web" 서비스 확인
- 상태: **Deployed** 또는 **Building**
- 배포 URL 확인 (예: `https://xxx.up.railway.app`)
- 로그 확인: "Logs" 탭 클릭

#### Worker 서비스
- 서비스 목록에서 "worker" 서비스 확인
- 상태 확인
- 로그 확인

### 3. 환경 변수 확인
각 서비스의 "Variables" 탭에서:
- `DATABASE_URL` 설정 확인
- `OPENAI_API_KEY` 설정 확인
- `APIFY_TOKEN` 설정 확인 (Worker만)
- `SERPAPI_KEY` 설정 확인 (Worker만)

---

## 방법 2: 로컬에서 Railway CLI 사용

### 사전 준비
```bash
# Railway CLI 설치 확인
railway --version

# Railway 로그인 (이미 로그인되어 있으면 스킵)
railway login

# 프로젝트 연결 확인
railway link
```

### 배포 상태 확인
```bash
# 프로젝트 디렉토리로 이동
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 서비스 상태 확인
railway status

# 최근 로그 확인
railway logs --tail 50

# 특정 서비스 로그 확인
railway logs --service streamlit --tail 50
railway logs --service worker --tail 50
```

---

## 방법 3: 배포 URL 직접 접속 테스트

### Streamlit 대시보드 테스트
1. Railway 대시보드에서 Streamlit 서비스의 배포 URL 확인
2. 브라우저에서 URL 접속
3. 대시보드가 정상 로드되는지 확인
4. 각 탭이 정상 작동하는지 확인

### 예상되는 문제
- **502 Bad Gateway**: 서비스가 아직 배포 중이거나 오류 발생
- **Database connection error**: `DATABASE_URL` 환경 변수 미설정
- **No data available**: 정상 (아직 데이터 수집 안 함)

---

## 방법 4: 로컬에서 배포 테스트

### Streamlit 로컬 실행
```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 환경 변수 설정
export DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway"

# Streamlit 실행
streamlit run web/app.py
```

### Worker 로컬 실행
```bash
# 환경 변수 설정
export DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway"
export OPENAI_API_KEY="sk-proj-..."
export APIFY_TOKEN="apify_api_..."
export SERPAPI_KEY="1180f58f3ddb13ffd66d47f742698a0a721150272742b7aa101a33a0d93963ef"

# Dry run 테스트
python worker/run_pipeline.py --mode=collect --dry-run
```

---

## 체크리스트

### Web 서비스 (Streamlit)
- [ ] Railway 대시보드에서 서비스 상태 확인
- [ ] 배포 URL 접속 테스트
- [ ] 대시보드 로드 확인
- [ ] 데이터베이스 연결 확인 (에러 없음)
- [ ] 각 탭 정상 작동 확인

### Worker 서비스
- [ ] Railway 대시보드에서 서비스 상태 확인
- [ ] 환경 변수 설정 확인
- [ ] 로그 확인 (에러 없음)
- [ ] 수동 실행 테스트 (선택사항)

### 데이터베이스
- [ ] PostgreSQL 서비스 상태 확인
- [ ] `DATABASE_URL` 환경 변수 확인
- [ ] 테이블 존재 확인 (마이그레이션 완료)

---

## 문제 해결

### 서비스가 배포되지 않음
1. Railway 대시보드에서 "Deploy" 버튼 클릭
2. GitHub 저장소 연결 확인
3. Dockerfile 경로 확인

### 환경 변수 오류
1. Railway 대시보드 → 서비스 → Variables 탭
2. 필수 환경 변수 추가:
   - `DATABASE_URL` (PostgreSQL 플러그인에서 자동 주입)
   - `OPENAI_API_KEY`
   - `APIFY_TOKEN` (Worker만)
   - `SERPAPI_KEY` (Worker만)

### 데이터베이스 연결 오류
1. PostgreSQL 플러그인 상태 확인
2. `DATABASE_URL` 환경 변수 확인
3. 마이그레이션 실행 확인

---

## 다음 단계

배포 확인 완료 후:
1. 실제 데이터 수집 실행
2. 파이프라인 전체 실행
3. 대시보드에서 결과 확인
