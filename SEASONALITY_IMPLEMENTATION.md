# 카테고리별 시즌성 해석 로직 구현 완료

## 목표
월 단위 시계열 생성 + 카테고리별 시즌성 해석 차등 적용 + LLM 브리프 생성 시 시즌성 정보 포함

---

## 구현된 기능

### 1. 카테고리 분류 (`config.py`)

#### 시즌성 카테고리 (SEASONAL_CATEGORIES)
- `SPRING_RECIPES`
- `SPRING_KITCHEN_STYLING`

#### 비시즌성 카테고리 (EVERGREEN_CATEGORIES)
- `REFRIGERATOR_ORGANIZATION`
- `VEGETABLE_PREP_HANDLING`

---

### 2. 월 단위 시계열 생성 (`timeseries.py`)

#### 기본 월 집계 (공통)
- `reddit_post_count`: 월별 포스트 수
- `reddit_weighted_score`: `log1p(upvotes) + 0.5 * log1p(num_comments)`

#### 시즌성 카테고리 해석 로직
1. **봄 시즌 정의**: March, April, May (3, 4, 5월)
2. **Spring Baseline 계산**:
   - 봄 시즌 historical baseline (다년치 데이터)
   - 다년치 없으면 전체 월 평균 사용
3. **Spring Adjusted Lift**:
   - `(current_spring_score - spring_baseline_score) / spring_baseline_score`
4. **트렌드 해석**:
   - `SEASONAL_EXPECTED`: 봄 시즌 정상 패턴 (baseline ±20% 이내)
   - `SEASONAL_OUTPERFORM`: 봄 시즌 기대치 대비 초과 상승 (>20%)
   - `SEASONAL_UNDERPERFORM`: 봄 시즌 대비 반응 약함 (<-20%)

#### 비시즌성 카테고리 해석 로직
1. **절대 증가 기준**: 시즌 baseline 보정 없음
2. **트렌드 해석**:
   - `EMERGING`: 최근 급상승 (30% 이상 증가)
   - `STEADY`: 지속적 관심 (±20% 이내)
   - `DECLINING`: 관심 감소 (-20% 이상)

---

### 3. Scoring 로직 (`scoring.py`)

#### `calculate_trend_status_with_seasonality()`
- 카테고리별 시즌성 해석 로직 적용
- 시즌성 카테고리: 봄 baseline 기반 해석
- 비시즌성 카테고리: 절대 증가 기준 해석
- `trend_metadata` 반환: 카테고리, baseline, lift 등 상세 정보

---

### 4. LLM 브리프 생성 (`labeling.py`)

#### LLM 프롬프트에 포함되는 정보
1. **카테고리 컨텍스트**:
   - Category: `SPRING_RECIPES` 등
   - Category Type: `SEASONAL` 또는 `EVERGREEN`
   - Trend Interpretation: `seasonality-adjusted` 또는 `non-seasonal (absolute growth)`
   - Trend Status: `SEASONAL_OUTPERFORM`, `EMERGING` 등
   - Trend Details: 상세 해석 정보

2. **Why-now 생성 규칙 (카테고리별 차등)**:
   - **시즌성 카테고리**:
     - ❌ "봄이라서" 단독 사용 금지
     - ✅ "기대 대비 초과/미달" 근거 필수 포함
     - SEASONAL_OUTPERFORM: 왜 봄 기대치를 초과하는지
     - SEASONAL_UNDERPERFORM: 왜 봄인데 반응이 약한지
   
   - **비시즌성 카테고리**:
     - ✅ 절대 상승/최근 가중 상승을 근거로 사용
     - 계절 언급은 보조적 맥락으로만 허용
     - EMERGING/STEADY/DECLINING 패턴 중심

---

## 실행 커맨드

### 1. Analyze 모드 (시계열 포함)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze
```

### 2. Label 모드 (시즌성 해석 포함)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=label --max-briefs=20
```

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

### 2. 카테고리별 분포 확인

```sql
-- 클러스터 카테고리 추정 (키워드 기반)
SELECT DISTINCT
    ca.cluster_id,
    rp.keyword
FROM cluster_assignments ca
JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
WHERE ca.created_from_run_id = ?
ORDER BY ca.cluster_id
LIMIT 20;
```

### 3. 트렌드 상태 확인

```sql
-- Brief별 트렌드 상태 (scoring 결과)
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

## 주요 특징

### 시즌성 해석의 차별화
- **시즌성 카테고리**: "봄이라서 늘어난 것"은 인사이트가 아님
- **비시즌성 카테고리**: 봄 시즌 증가는 "생활 리셋/정리 욕구" 같은 사회적 신호로 해석

### Why-now 생성 규칙
- 시즌성: 기대 대비 초과/미달 근거 필수
- 비시즌성: 절대 상승/최근 가중 상승 근거

### 재실행 안정성
- 모든 시계열 데이터는 upsert 기반
- `(cluster_id, month, created_from_run_id)` UNIQUE 제약

---

## 완료 조건

### ✅ Timeseries
- [ ] 월별 시계열 데이터 생성됨
- [ ] 시즌성 카테고리: 봄 baseline 계산됨
- [ ] 비시즌성 카테고리: 절대 증가 기준 적용됨

### ✅ Scoring
- [ ] 카테고리별 트렌드 해석 완료
- [ ] `trend_metadata` 생성됨

### ✅ Labeling
- [ ] LLM 프롬프트에 카테고리 타입 포함됨
- [ ] Why-now 생성 규칙 명시됨
- [ ] 시즌성/비시즌성 차등 적용됨

---

## 다음 단계

이 단계 완료 후:
- Streamlit 대시보드에서 시즌성 해석 결과 시각화
- 콘텐츠 기획에 활용
