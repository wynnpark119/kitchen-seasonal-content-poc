# Reddit 데이터 수집 시작 가이드

## 📊 수집 대상

- **총 키워드**: 100개
  - SPRING_RECIPES: 10개
  - SPRING_KITCHEN_STYLING: 30개
  - REFRIGERATOR_ORGANIZATION: 30개
  - VEGETABLE_PREP_HANDLING: 30개

- **수집 제한**:
  - 각 키워드당 최대 50개 포스트 (MAX_POSTS_PER_KEYWORD = 50)
  - 포스트당 상위 3개 댓글 (TOP_COMMENTS_PER_POST = 3)

---

## 🚀 실행 방법

### 1. 환경 변수 설정

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 필수 환경 변수
export DATABASE_URL="postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway"

# Apify API 토큰 (MCP를 사용하므로 선택사항)
# export APIFY_TOKEN="your-apify-token"
```

### 2. Reddit 수집 실행

```bash
# Reddit만 수집
python worker/run_pipeline.py --mode=collect --collect=reddit_only

# Dry run (테스트, DB 쓰기 없음)
python worker/run_pipeline.py --mode=collect --collect=reddit_only --dry-run
```

---

## 📋 수집 프로세스

1. **파이프라인 실행 시작**
   - `pipeline_runs` 테이블에 실행 기록 생성
   - run_id 생성

2. **키워드별 Reddit 수집**
   - Apify Actor를 사용하여 Reddit 포스트 수집
   - 각 키워드당 최대 50개 포스트
   - 포스트당 상위 3개 댓글 수집

3. **데이터베이스 저장**
   - `raw_reddit_posts` 테이블에 저장
   - `raw_reddit_comments` 테이블에 저장
   - upsert 방식으로 중복 방지

4. **수집 통계**
   - 수집된 포스트 수
   - 수집된 댓글 수
   - 처리된 키워드 수
   - 에러 발생 시 에러 로그

---

## ✅ 수집 완료 후 확인

### 데이터베이스 확인

```bash
# 수집된 포스트 수 확인
python migrations/run_query.py "SELECT COUNT(*) FROM raw_reddit_posts;"

# 키워드별 포스트 수 확인
python migrations/run_query.py "SELECT keyword, COUNT(*) as count FROM raw_reddit_posts GROUP BY keyword ORDER BY count DESC LIMIT 20;"

# 수집된 댓글 수 확인
python migrations/run_query.py "SELECT COUNT(*) FROM raw_reddit_comments;"
```

### 대시보드 확인

1. Streamlit 대시보드 접속: https://streamlit-production-eac8.up.railway.app
2. **Raw Data Explorer** 탭 확인
3. Reddit 포스트 목록이 표시되는지 확인

---

## ⚠️ 주의사항

- Apify MCP를 사용하므로 실제 Actor 호출은 AI Assistant가 수행합니다
- 수집 시간: 키워드당 약 1-2분 소요 (100개 키워드 = 약 2-3시간)
- 비용: Apify 사용량에 따라 비용 발생 가능

---

## 🎯 다음 단계

Reddit 수집 완료 후:
1. SERP AI Overview 수집 (`--mode=collect --collect=serp_only`)
2. 분석 파이프라인 실행 (`--mode=analyze`)
3. 라벨링 및 브리프 생성 (`--mode=label`)
