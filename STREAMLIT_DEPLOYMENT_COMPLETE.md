# Streamlit 배포 완료 확인 가이드

## ✅ 완료된 작업

1. 데이터베이스 마이그레이션 완료
2. DATABASE_URL 환경 변수 설정 완료
3. Streamlit 서비스 준비 완료

---

## 🔍 배포 상태 확인

### 1. Railway 대시보드에서 확인

1. Railway 대시보드 접속: https://railway.app
2. 프로젝트 선택
3. **Streamlit 서비스** 클릭
4. 확인 사항:
   - **상태**: "Active" 또는 "Running" (녹색)
   - **URL**: Streamlit 서비스 URL 확인 (예: `https://xxx.railway.app`)
   - **로그**: 에러가 없는지 확인

### 2. 대시보드 접속 테스트

Streamlit 서비스 URL로 접속:
- Railway 대시보드에서 Streamlit 서비스의 **"Open"** 또는 **"View"** 버튼 클릭
- 또는 직접 URL 접속

**예상 화면:**
- "🏠 LG Content Intelligence Dashboard" 제목 표시
- 6개 탭: Executive Overview, Raw Data Explorer, Cluster & Trend Explorer, Master Topic Explorer, SERP AIO Audit, Opportunity Matrix
- 데이터가 없으면 "No data available" 메시지 표시 (정상)

---

## 🧪 기능 테스트

### 1. 데이터베이스 연결 확인
- 대시보드가 로드되면 데이터베이스 연결 성공
- 에러 메시지가 없으면 정상

### 2. 각 탭 확인
- **TAB 0. Executive Overview**: 전체 요약 (데이터 없으면 0 표시)
- **TAB 1. Raw Data Explorer**: Reddit/SERP 데이터 (데이터 없으면 빈 테이블)
- **TAB 2. Cluster & Trend Explorer**: 클러스터 목록 (데이터 없으면 빈 목록)
- **TAB 3. Master Topic Explorer**: 마스터 토픽 카드 (데이터 없으면 빈 목록)
- **TAB 4. SERP AIO Audit**: AI Overview 감사 (데이터 없으면 빈 테이블)
- **TAB 5. Opportunity Matrix**: 기회 매트릭스 (데이터 없으면 빈 차트)

---

## ⚠️ 문제 해결

### 문제 1: "Application failed to respond"
**원인**: DATABASE_URL 미설정 또는 연결 실패
**해결**:
1. Railway 대시보드 → Streamlit 서비스 → Variables
2. DATABASE_URL이 설정되어 있는지 확인
3. Streamlit 서비스 재배포

### 문제 2: "DATABASE_URL 환경 변수가 설정되지 않았습니다"
**원인**: DATABASE_URL이 Streamlit 서비스에 없음
**해결**:
1. Railway 대시보드 → Streamlit 서비스 → Variables
2. DATABASE_URL 추가:
   ```
   postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway
   ```
3. 재배포

### 문제 3: 대시보드는 보이지만 데이터가 없음
**정상**: 아직 데이터를 수집하지 않았기 때문입니다.
**다음 단계**: 데이터 수집 파이프라인 실행

---

## 📊 다음 단계: 데이터 수집

대시보드가 정상 작동하면 데이터 수집을 시작할 수 있습니다:

1. **Reddit 포스트 수집**
   ```bash
   python worker/run_pipeline.py --mode=collect --collect=reddit_only
   ```

2. **SERP AI Overview 수집**
   ```bash
   python worker/run_pipeline.py --mode=collect --collect=serp_only
   ```

3. **전체 파이프라인 실행**
   ```bash
   python worker/run_pipeline.py --mode=all
   ```

---

## ✅ 체크리스트

- [x] 데이터베이스 마이그레이션 완료
- [x] DATABASE_URL 환경 변수 설정 완료
- [ ] Streamlit 서비스 배포 확인
- [ ] 대시보드 접속 테스트
- [ ] 데이터 수집 시작 (선택사항)

---

## 🎉 완료!

Streamlit 대시보드가 정상적으로 배포되었습니다!

데이터를 수집하면 대시보드에서 분석 결과를 확인할 수 있습니다.
