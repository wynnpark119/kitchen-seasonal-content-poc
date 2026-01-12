# 카테고리별 시즌성 해석 실행 가이드

## 목표
월 단위 시계열 생성 + 카테고리별 시즌성 해석 + LLM 브리프 생성 (시즌성 정보 포함)

---

## 실행 커맨드

### 1. Analyze 모드 (시계열 포함)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze
```

**예상 출력:**
```
Step 4: Starting timeseries generation (with seasonality interpretation)...
Generating timeseries for X clusters
Cluster 1 (SPRING_RECIPES): spring_baseline=12.34, count=3
Cluster 2 (REFRIGERATOR_ORGANIZATION): ...
Timeseries generation completed:
  Clusters processed: X
  Months aggregated: Y
  Seasonal clusters: Z
  Evergreen clusters: W
```

### 2. Label 모드 (시즌성 해석 포함)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=label --max-briefs=20
```

**예상 출력:**
```
Calculating priority scores for X clusters
Top 20 clusters selected:
  1. Cluster 1 (SPRING_RECIPES): score=125.50, status=SEASONAL_OUTPERFORM
  2. Cluster 2 (REFRIGERATOR_ORGANIZATION): score=98.30, status=EMERGING
  ...
Generating briefs for top 20 clusters (max_briefs=20)...
Brief created for cluster 1 (SPRING_RECIPES, score: 125.50, trend: SEASONAL_OUTPERFORM)
```

---

## 처리 단계

### Step 1: Timeseries 생성
- 월별 집계: `reddit_post_count`, `reddit_weighted_score`
- 카테고리 확인: 키워드 기반 추정
- 시즌성/비시즌성 분류

### Step 2: Scoring (시즌성 해석)
- 시즌성 카테고리: 봄 baseline 계산 → spring_adjusted_lift → 트렌드 해석
- 비시즌성 카테고리: 절대 증가 기준 → 트렌드 해석

### Step 3: Labeling (LLM 브리프 생성)
- 카테고리 타입 및 시즌성 해석 정보를 LLM 프롬프트에 포함
- Why-now 생성 규칙 명시 (시즌성/비시즌성 차등)

---

## 검증 SQL

### 1. 시계열 데이터 확인

```sql
-- 클러스터별 월별 시계열
SELECT 
    ct.cluster_id,
    ct.month,
    ct.reddit_post_count,
    ct.reddit_weighted_score
FROM cluster_timeseries ct
WHERE ct.created_from_run_id = ?
ORDER BY ct.cluster_id, ct.month DESC
LIMIT 20;
```

### 2. 봄 시즌 데이터 확인

```sql
-- 봄 시즌 (3, 4, 5월) 시계열
SELECT 
    ct.cluster_id,
    ct.month,
    ct.reddit_weighted_score,
    EXTRACT(MONTH FROM ct.month) as month_num
FROM cluster_timeseries ct
WHERE ct.created_from_run_id = ?
AND EXTRACT(MONTH FROM ct.month) IN (3, 4, 5)
ORDER BY ct.cluster_id, ct.month DESC;
```

### 3. Brief별 트렌드 상태 확인

```sql
-- Brief와 클러스터 정보
SELECT 
    tqb.cluster_id,
    tqb.category,
    tqb.topic_title,
    tqb.score,
    c.size as cluster_size
FROM topic_qa_briefs tqb
JOIN clusters c ON tqb.cluster_id = c.cluster_id
WHERE tqb.created_from_run_id = ?
ORDER BY tqb.score DESC NULLS LAST
LIMIT 10;
```

---

## 완료 조건

### ✅ Timeseries
- [ ] 월별 시계열 데이터 생성됨
- [ ] 시즌성/비시즌성 카테고리 분류됨
- [ ] `reddit_weighted_score` 계산됨 (log1p 기반)

### ✅ Scoring
- [ ] 시즌성 카테고리: 봄 baseline 계산됨
- [ ] 비시즌성 카테고리: 절대 증가 기준 적용됨
- [ ] 트렌드 상태 계산됨 (SEASONAL_OUTPERFORM, EMERGING 등)

### ✅ Labeling
- [ ] LLM 프롬프트에 카테고리 타입 포함됨
- [ ] Why-now 생성 규칙 명시됨
- [ ] 시즌성/비시즌성 차등 적용됨

---

## 주요 특징

### 시즌성 해석의 차별화
- **시즌성 카테고리**: "봄이라서 늘어난 것"은 인사이트가 아님
- **비시즌성 카테고리**: 봄 시즌 증가는 "생활 리셋/정리 욕구" 같은 사회적 신호로 해석

### Why-now 생성 규칙
- 시즌성: 기대 대비 초과/미달 근거 필수
- 비시즌성: 절대 상승/최근 가중 상승 근거

---

## 다음 단계

이 단계 완료 후:
- Streamlit 대시보드에서 시즌성 해석 결과 시각화
- 콘텐츠 기획에 활용
