# 다음 단계: 데이터 수집 시작

## ✅ 현재 상태

대시보드가 정상적으로 작동하고 있습니다!
- ✅ Streamlit 대시보드 로드 완료
- ✅ 데이터베이스 연결 완료
- ✅ 모든 탭 정상 표시
- ℹ️  데이터 없음 (아직 수집하지 않음)

---

## 📊 데이터 수집 시작

대시보드에 데이터를 표시하려면 데이터 수집 파이프라인을 실행해야 합니다.

### 1. Reddit 포스트 수집

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
export DATABASE_URL="postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway"
export OPENAI_API_KEY="your-openai-api-key"

# Reddit 포스트 수집
python worker/run_pipeline.py --mode=collect --collect=reddit_only
```

### 2. SERP AI Overview 수집

```bash
# SERP AI Overview 수집
python worker/run_pipeline.py --mode=collect --collect=serp_only
```

### 3. 전체 파이프라인 실행

```bash
# 전체 파이프라인 (수집 → 분석 → 라벨링)
python worker/run_pipeline.py --mode=all
```

---

## 🔍 데이터 수집 후 확인

데이터 수집이 완료되면:

1. **대시보드 새로고침**
   - Streamlit URL: https://streamlit-production-eac8.up.railway.app
   - 브라우저에서 새로고침 (F5 또는 Cmd+R)

2. **Executive Overview 확인**
   - Total Master Topics: 0보다 큰 값 표시
   - 각 지표가 업데이트됨

3. **다른 탭 확인**
   - Raw Data Explorer: Reddit 포스트 목록
   - Cluster & Trend Explorer: 클러스터 목록
   - Master Topic Explorer: 마스터 토픽 카드

---

## 📋 필요한 환경 변수

데이터 수집을 위해 다음 환경 변수가 필요합니다:

- `DATABASE_URL`: 이미 설정됨 ✅
- `OPENAI_API_KEY`: OpenAI API 키 (임베딩 및 LLM 호출용)
- `SERPAPI_KEY`: SerpAPI 키 (SERP AI Overview 수집용, 선택사항)
- `APIFY_API_TOKEN`: Apify 토큰 (Reddit 수집용, 선택사항)

---

## 🎉 완료!

대시보드가 정상적으로 작동하고 있습니다. 이제 데이터를 수집하면 대시보드에 표시됩니다!
