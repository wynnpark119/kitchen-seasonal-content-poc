# Reddit 데이터 프루닝 최종 요약

## 실행 절차

### 1단계: 샘플 추출
```sql
-- 각 키워드별 상위 10개 포스트 추출
SELECT 
    keyword,
    reddit_post_id,
    title,
    body,
    subreddit,
    upvotes,
    num_comments
FROM raw_reddit_posts
WHERE keyword = ?
ORDER BY upvotes DESC, num_comments DESC
LIMIT 10;

-- 각 포스트의 Top 1-2 댓글
SELECT body, upvotes, author
FROM raw_reddit_comments
WHERE reddit_post_id = ?
ORDER BY upvotes DESC
LIMIT 2;
```

### 2단계: 포스트 단위 판정
각 포스트에 대해 다음 순서로 판정:
1. 즉시 제거 조건 체크 → 해당 시 **DROP**
2. 조건부 제거 조건 체크 → 대부분 **DROP**
3. 유지 조건 체크 → 해당 시 **KEEP**
4. 4대 주제별 핵심 질문 적용 → 매핑 가능 여부 확인
5. 위 조건 모두 해당 안 되면 **REVIEW**

### 3단계: 키워드 단위 판정
키워드별 샘플 10개 판정 결과 집계:
- 오탐 비율 계산
- 주제 일관성 평가
- 구매/고장 비율 계산
- 후보 조건 2개 이상 → **DROP 확정**

### 4단계: 필터링 적용
1. Negative keywords 정규식 적용
2. 즉시 제거 조건 SQL WHERE 절 적용
3. DROP 키워드의 모든 포스트 제거

---

## 판정 결과 (예상)

### 키워드 최종 리스트

#### SPRING_RECIPES
**KEEP (예상):**
- spring dinner ideas
- easy spring meals
- what to cook in spring
- spring meal prep
- light spring recipes
- quick spring dinner
- spring weeknight meals
- healthy spring meals
- what do you cook in spring
- best spring dinner ideas

**DROP (예상):**
- spring recipe book → **근거:** 샘플 10개 중 8개가 책 추천/구매 관련
- spring recipe app → **근거:** 샘플 10개 중 9개가 앱 추천
- spring recipe subscription → **근거:** 구독 서비스 중심
- spring recipe meal kit → **근거:** 배송 서비스 중심

#### SPRING_KITCHEN_STYLING
**KEEP (예상):**
- spring kitchen decor
- kitchen spring refresh
- spring table setting ideas
- how to decorate kitchen for spring
- spring kitchen ideas
- kitchen spring makeover
- spring kitchen styling
- spring home decor kitchen

**DROP (예상):**
- spring kitchen fashion → **근거:** 패션 오탐 (샘플 10개 중 7개가 패션 관련)
- spring kitchen hair styling → **근거:** 헤어 스타일링 오탐
- spring kitchen makeup → **근거:** 메이크업 오탐

#### REFRIGERATOR_ORGANIZATION
**KEEP (예상):**
- refrigerator organization
- fridge organization tips
- how to organize refrigerator
- refrigerator storage ideas
- fridge organization system
- refrigerator organization hacks
- how do you organize your fridge
- best way to organize fridge

**DROP (예상):**
- refrigerator repair → **근거:** 샘플 10개 중 9개가 고장/수리 관련
- refrigerator not cooling → **근거:** 고장 중심
- refrigerator warranty → **근거:** 보증/AS 중심
- refrigerator replacement → **근거:** 교체 중심
- refrigerator buying guide → **근거:** 구매 중심
- refrigerator reviews → **근거:** 제품 리뷰 중심

#### VEGETABLE_PREP_HANDLING
**KEEP (예상):**
- vegetable prep
- how to prep vegetables
- vegetable storage tips
- how to store vegetables
- vegetable washing tips
- how to wash vegetables
- vegetable prep meal prep
- best way to prep vegetables

**DROP (예상):**
- vegetable gardening → **근거:** 샘플 10개 중 7개가 재배/가드닝 관련
- vegetable planting → **근거:** 재배 중심
- vegetable seeds → **근거:** 재배 중심
- vegetable growing → **근거:** 재배 중심
- vegetable fertilizer → **근거:** 재배 중심
- vegetable soil → **근거:** 재배 중심

---

## 포스트 필터링 룰

### Negative Keywords (정규식)

#### 구매/비교
```regex
\b(buy|purchase|price|cost|affordable|cheap|expensive|worth it|recommend|review|comparison|vs|which one|better|best brand|where to buy|deal|sale|discount)\b
```

#### 고장/수리/AS
```regex
\b(not cooling|broken|repair|error code|warranty|compressor|ice maker|defrost|leaking|not working|stopped|faulty|malfunction|service|technician|fix|damaged)\b
```

#### 오탐 방지
```regex
\b(spring break|spring mattress|coil spring|engine spring|spring water|hair styling|fashion styling|nail styling|makeup styling|vegetable gardening|vegetable planting|vegetable seeds|vegetable growing)\b
```

#### 브랜드/모델
```regex
\b(model|spec|specification|Samsung|LG|Whirlpool|KitchenAid|GE|Bosch|Maytag|Frigidaire)\b
```

### SQL 필터링 예시
```sql
-- 즉시 제거 조건 적용
DELETE FROM raw_reddit_posts
WHERE 
    -- 구매/추천 패턴
    (title ~* '\y(buy|purchase|price|recommend|worth it|vs|which one)\y'
     OR body ~* '\y(buy|purchase|price|recommend|worth it|vs|which one)\y')
    OR
    -- 고장/수리 패턴
    (title ~* '\y(not cooling|broken|repair|error code|warranty|compressor)\y'
     OR body ~* '\y(not cooling|broken|repair|error code|warranty|compressor)\y')
    OR
    -- 오탐 패턴
    (title ~* '\y(spring break|spring mattress|hair styling|vegetable gardening)\y'
     OR body ~* '\y(spring break|spring mattress|hair styling|vegetable gardening)\y')
    OR
    -- 정보 밀도 낮음
    (LENGTH(COALESCE(body, '')) < 50 AND num_comments <= 1);
```

---

## PoC 권장 컷 비율

### 포스트 제거 목표
- **목표:** 30~40% 제거
- **최소:** 20% 제거
- **최대:** 50% 제거

### 키워드 제거 목표
- **목표:** 20~30% 제거
- **최소:** 10% 제거
- **최대:** 40% 제거

### 판정 분류 목표
- **KEEP:** 70~80%
- **DROP:** 20~30%
- **REVIEW:** 5% 이하 (최소화)

---

## 정제 완료 조건 (analyze 단계 전)

### ✅ 데이터 품질
- [ ] 각 키워드별 최소 10개 이상 유효 포스트
- [ ] 오탐/노이즈 포스트 제거 완료
- [ ] 4대 주제별로 최소 1개 키워드 이상 유지

### ✅ 키워드 정제
- [ ] DROP 키워드 제거 완료
- [ ] REVIEW 키워드 판정 완료 (KEEP 또는 DROP 결정)
- [ ] 최종 키워드 리스트 확정

### ✅ 포스트 필터링
- [ ] Negative keywords 적용 완료
- [ ] 즉시 제거 조건 적용 완료
- [ ] 조건부 제거 판정 완료

### ✅ 컷 비율 달성
- [ ] 포스트 30~40% 제거 목표 달성
- [ ] 키워드 20~30% 제거 목표 달성

### ✅ 데이터베이스 상태
- [ ] `raw_reddit_posts`에 유효 포스트만 남음
- [ ] `pipeline_runs`에 정제 상태 기록

---

## 다음 단계

정제 완료 후 `analyze` 단계로 진행:
```bash
python worker/run_pipeline.py --mode=analyze
```

이 단계에서:
- 정제된 포스트로 임베딩 생성
- HDBSCAN 클러스터링
- 클러스터별 특징어 추출
- 시계열 분석

---

## 참고 파일

- `PRUNING_RULES.md` - 상세 프루닝 규칙
- `PRUNING_EXECUTION.md` - 실행 절차
- `pruning.py` - 프루닝 모듈 코드
