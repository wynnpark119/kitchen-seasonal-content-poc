# Label Mode 실행 가이드

## 목표
클러스터 단위로만 LLM 호출하여 topic_qa_briefs 생성 + 인사이트 모듈 6개 필드 추가

---

## 주요 기능

### 1. 우선순위 점수 기반 클러스터 선정
- **점수 계산식**: `reddit_weighted_score (최근 3개월 가중) + GSC impressions - AIO AVAILABLE 페널티`
- **상위 N개만 처리**: 기본 20개, `--max-briefs` 옵션으로 조정 가능
- **트렌드 상태**: Emerging, Competitive, Saturated, Niche 자동 태그

### 2. 인사이트 모듈 6개 필드
1. **content_gap_analysis**: AIO 커버리지 + 차별화 포인트
2. **execution_checklist**: 콘텐츠 제작 단계 체크리스트 (6-10단계)
3. **publishing_window**: 권장 발행 시기 (월 단위 시계열 기반)
4. **format_recommendations**: 블로그/소셜 포맷 추천
5. **evidence_strength**: 증거 강도 점수 (0-100) + 기여 요소
6. **safety_and_claims_flags**: 안전성/클레임 리스크 플래그

### 3. GSC/AIO 처리 규칙
- **GSC 없으면**: "not available" 명시 (추론 금지)
- **AIO 없으면**: "NOT_AVAILABLE" 명시 (추론 금지)
- **AIO 있으면**: aio_text 요약 + cited_sources 5개

---

## 데이터베이스 마이그레이션

### insights_json 컬럼 추가

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
python3 -c "
import psycopg2
import os
with open('migrations/003_add_insights_json.sql', 'r') as f:
    sql = f.read()
conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway'))
cur = conn.cursor()
cur.execute(sql)
conn.commit()
print('Migration completed')
"
```

---

## 실행 커맨드

### 1. Dry-run (샘플 처리만)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key" \
python3 worker/run_pipeline.py --mode=label --dry-run --max-briefs=5
```

### 2. 실제 실행 (기본 20개)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key" \
python3 worker/run_pipeline.py --mode=label
```

### 3. 최대 개수 지정

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key" \
python3 worker/run_pipeline.py --mode=label --max-briefs=50
```

---

## 처리 단계

### Step 1: 우선순위 점수 계산 (scoring.py)
- Reddit weighted score (최근 3개월 가중: 1.0, 0.7, 0.5)
- GSC impressions 점수 (있으면)
- AIO AVAILABLE 페널티 (소폭 -5점)
- 트렌드 상태 계산 (Emerging/Competitive/Saturated/Niche)

### Step 2: 상위 N개 클러스터 선정
- 점수 내림차순 정렬
- 상위 N개만 선택 (기본 20개)

### Step 3: LLM 호출 (클러스터 단위)
- 대표 포스트 3-5개 (title + 1-2문장 요약)
- 특징어 top 10-15
- 월별 트렌드 요약
- GSC 요약 (있으면) 또는 "not available"
- SERP AIO 요약 (있으면) 또는 "NOT_AVAILABLE"

### Step 4: 인사이트 모듈 생성
- LLM이 6개 인사이트 필드 자동 생성
- `insights_json` (JSONB)로 저장

### Step 5: Evidence Pack 구성
- Reddit 포스트 3-5개 + 댓글 Top 1-3
- GSC 데이터 (있으면) 또는 "not available"
- SERP AIO (있으면) 또는 "NOT_AVAILABLE"

---

## 검증 SQL

### 1. Brief 생성 확인

```sql
-- 총 brief 수
SELECT COUNT(*) as total_briefs
FROM topic_qa_briefs
WHERE created_from_run_id = ?;

-- 카테고리별 분포
SELECT category, COUNT(*) as count
FROM topic_qa_briefs
WHERE created_from_run_id = ?
GROUP BY category
ORDER BY count DESC;
```

### 2. Insights JSON 확인

```sql
-- Insights JSON 샘플 조회
SELECT 
    cluster_id,
    topic_title,
    insights_json->'content_gap_analysis' as content_gap,
    insights_json->'execution_checklist' as checklist,
    insights_json->'publishing_window' as window,
    insights_json->'format_recommendations' as formats,
    insights_json->'evidence_strength' as strength,
    insights_json->'safety_and_claims_flags' as safety_flags
FROM topic_qa_briefs
WHERE created_from_run_id = ?
AND insights_json IS NOT NULL
LIMIT 5;
```

### 3. 우선순위 점수 확인

```sql
-- 점수별 정렬
SELECT 
    cluster_id,
    topic_title,
    score,
    category
FROM topic_qa_briefs
WHERE created_from_run_id = ?
ORDER BY score DESC NULLS LAST
LIMIT 10;
```

### 4. 인사이트 모듈 상세 확인

```sql
-- Content Gap Analysis
SELECT 
    topic_title,
    insights_json->'content_gap_analysis'->>'aio_coverage' as aio_coverage,
    insights_json->'content_gap_analysis'->'differentiation_points' as diff_points
FROM topic_qa_briefs
WHERE created_from_run_id = ?
AND insights_json IS NOT NULL
LIMIT 5;

-- Publishing Window
SELECT 
    topic_title,
    insights_json->'publishing_window'->>'recommended_window' as window,
    insights_json->'publishing_window'->>'rationale' as rationale
FROM topic_qa_briefs
WHERE created_from_run_id = ?
AND insights_json IS NOT NULL
LIMIT 5;

-- Evidence Strength
SELECT 
    topic_title,
    (insights_json->'evidence_strength'->>'score')::int as score,
    insights_json->'evidence_strength'->'drivers' as drivers
FROM topic_qa_briefs
WHERE created_from_run_id = ?
AND insights_json IS NOT NULL
ORDER BY (insights_json->'evidence_strength'->>'score')::int DESC
LIMIT 10;
```

---

## 완료 조건

### ✅ Brief 생성
- [ ] 상위 N개 클러스터에 대해 brief 생성됨
- [ ] 모든 brief에 `insights_json` 포함됨
- [ ] `(cluster_id, model_version)` UNIQUE 제약 만족

### ✅ 인사이트 모듈
- [ ] 6개 필드 모두 생성됨:
  - [ ] content_gap_analysis
  - [ ] execution_checklist
  - [ ] publishing_window
  - [ ] format_recommendations
  - [ ] evidence_strength
  - [ ] safety_and_claims_flags

### ✅ GSC/AIO 처리
- [ ] GSC 없으면 "not available" 명시
- [ ] AIO 없으면 "NOT_AVAILABLE" 명시
- [ ] 추론 없이 명시적으로 표기

### ✅ 우선순위 점수
- [ ] 모든 brief에 score 계산됨
- [ ] 상위 N개만 처리됨 (기본 20개)

---

## 예상 실행 시간

- **우선순위 점수 계산**: ~5-10초 (클러스터 수에 따라)
- **LLM 호출**: ~20-30초/brief (gpt-4o-mini 기준)
- **총 예상 시간**: 20개 brief 기준 ~7-10분

---

## 주의사항

1. **OpenAI API 키 필요**: `OPENAI_API_KEY` 환경변수 필수
2. **비용**: gpt-4o-mini는 유료 모델입니다
3. **클러스터 전제**: `--mode=analyze` 완료 후 실행해야 함
4. **GSC/AIO 없음**: 정상 동작하며 "not available"로 명시됨

---

## 다음 단계

Label 모드 완료 후:
- Streamlit 대시보드에서 brief 및 insights 시각화
- 콘텐츠 기획에 활용
