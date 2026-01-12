# Reddit 데이터 프루닝 규칙 (Pruning Rules)

## 목적
PoC 특성상 노이즈 최소화가 최우선. 애매하면 제거하는 보수적 필터링 원칙.

---

## 1. 포스트 즉시 제거(Kill) 조건

하나라도 해당되면 즉시 제거.

### 1.1 구매/추천/비교 관련
**패턴:**
- "which should I buy", "worth it", "recommend", "vs", "best brand"
- "what to buy", "where to buy", "price", "cost", "affordable"
- "review", "comparison", "which one", "better"

**예시:**
- ❌ "Which refrigerator should I buy? Samsung vs LG"
- ❌ "Is this worth the price?"
- ❌ "Best brand for vegetable storage containers?"

### 1.2 고장/수리/AS 관련
**패턴:**
- "not cooling", "broken", "repair", "error code", "warranty"
- "compressor", "ice maker", "defrost", "leaking"
- "not working", "stopped", "faulty", "malfunction"

**예시:**
- ❌ "My refrigerator is not cooling, what's wrong?"
- ❌ "Ice maker repair cost"
- ❌ "Error code E3 on my fridge"

### 1.3 가전/브랜드 중심
**패턴:**
- 모델명/스펙/가격이 본문 중심
- 제품명이 제목에 포함되고 본문이 제품 리뷰/비교

**예시:**
- ❌ "Samsung RF28R7351SG Review"
- ❌ "LG LRFVS3006S specs and price"

### 1.4 시즌/라이프스타일 무관
**패턴:**
- 계절 맥락 없이 상시 일반 잡담/링크 공유
- "spring"이 키워드에 있지만 봄/계절과 무관한 내용

**예시:**
- ❌ "Spring mattress recommendations" (spring = 스프링)
- ❌ "Spring break vacation ideas" (spring break = 방학)

### 1.5 노이즈 오탐
**패턴:**

#### "spring" 오탐
- mattress spring (매트리스 스프링)
- coil spring (코일 스프링)
- engine spring (엔진 스프링)
- spring break (방학)
- spring water (샘물)

#### "styling" 오탐
- hair styling (헤어 스타일링)
- fashion styling (패션 스타일링)
- nail styling (네일 스타일링)
- makeup styling (메이크업)

#### "vegetable" 오탐
- vegetable gardening (재배)
- vegetable planting (식재)
- vegetable seeds (종자)
- vegetable growing (재배)

---

## 2. 조건부 제거(대부분 제거) 조건

다음 조건에 해당하면 대부분 제거. 예외적으로 유지하려면 명확한 근거 필요.

### 2.1 지나치게 개인 사정/특수 상황
**판정:**
- 일반화 어려운 매우 특수한 상황
- 다른 사람에게 적용 불가능한 개인적 문제

**예시:**
- ⚠️ "My 1970s refrigerator that my grandma gave me..."
- ⚠️ "I have a 2x2 foot kitchen, how do I organize?"

### 2.2 댓글 반응 거의 없음 + 질문 막연함
**판정:**
- 댓글 0~1개
- 질문이 "any tips?" 수준으로 막연함
- 구체적인 고민/상황 설명 없음

**예시:**
- ⚠️ "Any tips for spring cooking?" (본문 없음, 댓글 0개)
- ⚠️ "How do you organize your fridge?" (본문 1줄, 댓글 1개)

### 2.3 정보 밀도 낮음
**판정:**
- 본문이 거의 없음 (10단어 미만)
- 링크 공유만 있음
- 이미지/비디오 링크만 있음

**예시:**
- ⚠️ "Check this out: [link]" (본문 없음)
- ⚠️ "Spring recipe" (본문 없음, 이미지만)

### 2.4 키워드 억지 매칭
**판정:**
- 제목만 키워드 포함, 본문은 완전히 무관
- 키워드가 우연히 등장했을 뿐 주제와 무관

**예시:**
- ⚠️ 제목: "Spring dinner ideas" / 본문: "I'm going to a spring wedding, what should I wear?"

---

## 3. 유지(Keep) 조건

다음 조건을 만족하면 유지.

### 3.1 실제 생활자 고민이 명확
- Q&A/How-to로 전환 가능한 구체적 질문
- "왜", "어떻게", "언제" 등이 명확

**예시:**
- ✅ "How do you keep spring vegetables fresh longer?"
- ✅ "What's the best way to organize a small refrigerator?"

### 3.2 댓글에 경험 공유/토론 존재
- 댓글에 실제 경험/팁/토론이 있음
- 댓글 수 3개 이상 또는 상위 댓글 upvotes 10 이상

**예시:**
- ✅ "I use glass containers for meal prep" (댓글 15개, 경험 공유 많음)

### 3.3 계절/봄 맥락 또는 라이프스타일 맥락 분명
- 봄/계절적 특성이 드러남
- 라이프스타일 개선/변화 맥락이 있음

**예시:**
- ✅ "Spring vegetables are in season, what recipes do you make?"
- ✅ "I want to refresh my kitchen for spring, any ideas?"

### 3.4 4대 주제 중 하나로 자연스럽게 매핑 가능
- SPRING_RECIPES
- SPRING_KITCHEN_STYLING
- REFRIGERATOR_ORGANIZATION
- VEGETABLE_PREP_HANDLING

---

## 4. 키워드 단위 삭제(Keyword Kill) 규칙

### 4.1 키워드 삭제 후보 조건
다음 중 하나라도 해당하면 후보:

1. **오탐/제외 대상 50% 이상**
   - 키워드별 샘플 10개 중 5개 이상이 오탐/제외 대상

2. **주제 분산**
   - 샘플 10개 중 주제가 너무 분산되어 공통점 부족
   - 키워드로 검색했지만 실제 주제가 일관되지 않음

3. **구매/고장/AS 주류**
   - 샘플 10개 중 5개 이상이 구매/고장/AS 관련

### 4.2 키워드 삭제 확정
위 후보 조건 중 **2개 이상**에 해당하면 삭제 확정.

---

## 5. 4대 주제별 유지 핵심 질문

각 포스트를 다음 질문으로 판정:

### 5.1 SPRING_RECIPES
**핵심 질문:** "이 포스트로 블로그 글 1편을 쓸 수 있는가?"

**판정 기준:**
- 봄 제철 재료 활용법이 드러나는가?
- 가벼운/건강한 식단 맥락이 있는가?
- 가족/혼밥/주말 요리 맥락이 있는가?

**예시:**
- ✅ "What spring vegetables do you use for meal prep?"
- ❌ "Spring recipe book recommendations"

### 5.2 SPRING_KITCHEN_STYLING
**핵심 질문:** "주방 분위기/연출을 왜/어떻게 바꾸는지 드러나는가?"

**판정 기준:**
- 주방 인테리어/데코 아이디어가 있는가?
- 봄 분위기 연출(컬러, 식기, 소품)이 드러나는가?
- 홈 파티/테이블 세팅 맥락이 있는가?

**예시:**
- ✅ "How do you decorate your kitchen for spring?"
- ❌ "Spring kitchen fashion trends"

### 5.3 REFRIGERATOR_ORGANIZATION
**핵심 질문:** "정리 원칙/루틴/보관 고민이 드러나는가? (고장/AS는 제외)"

**판정 기준:**
- 냉장고 정리/보관 노하우가 있는가?
- 계절 식재료 보관법이 드러나는가?
- 정리 루틴/공간 활용 팁이 있는가?

**예시:**
- ✅ "How do you organize your refrigerator for meal prep?"
- ❌ "My refrigerator is not cooling"

### 5.4 VEGETABLE_PREP_HANDLING
**핵심 질문:** "요리 전 손질/세척/보관의 헷갈림 포인트인가? (가드닝 제외)"

**판정 기준:**
- 야채 세척/손질/보관 팁이 있는가?
- 미리 손질해두는 방법이 드러나는가?
- 신선도 유지 팁이 있는가?

**예시:**
- ✅ "How do you prep vegetables for the week?"
- ❌ "How to grow vegetables in spring"

---

## 6. Negative Keywords (정규식/키워드 기반)

포스트 필터링에 사용할 negative keywords:

### 6.1 구매/비교 관련
```
buy|purchase|price|cost|affordable|cheap|expensive|worth it|recommend|review|comparison|vs|which one|better|best brand|where to buy|deal|sale|discount
```

### 6.2 고장/수리/AS 관련
```
not cooling|broken|repair|error code|warranty|compressor|ice maker|defrost|leaking|not working|stopped|faulty|malfunction|service|technician|fix|broken|damaged
```

### 6.3 오탐 방지
```
spring break|spring mattress|coil spring|engine spring|spring water|hair styling|fashion styling|nail styling|makeup styling|vegetable gardening|vegetable planting|vegetable seeds|vegetable growing
```

### 6.4 모델명/브랜드 중심
```
model|spec|specification|Samsung|LG|Whirlpool|KitchenAid|GE|Bosch|Maytag|Frigidaire
```

---

## 7. PoC 권장 컷 비율

### 7.1 포스트 제거 목표
- **목표:** 30~40% 제거
- **최소:** 20% 제거
- **최대:** 50% 제거 (너무 많이 제거하면 데이터 부족)

### 7.2 키워드 제거 목표
- **목표:** 20~30% 제거
- **최소:** 10% 제거
- **최대:** 40% 제거

### 7.3 판정 분류
- **KEEP:** 명확히 유지 (70~80%)
- **DROP:** 명확히 제거 (20~30%)
- **REVIEW:** 애매한 경우 (최소화, 5% 이하)

---

## 8. 정제 완료 조건 (analyze 단계 전)

다음 조건을 모두 만족해야 `analyze` 단계로 진행:

### 8.1 데이터 품질
- [ ] 각 키워드별 최소 10개 이상 유효 포스트
- [ ] 오탐/노이즈 포스트 제거 완료
- [ ] 4대 주제별로 최소 1개 키워드 이상 유지

### 8.2 키워드 정제
- [ ] DROP 키워드 제거 완료
- [ ] REVIEW 키워드 판정 완료 (KEEP 또는 DROP 결정)
- [ ] 최종 키워드 리스트 확정

### 8.3 포스트 필터링
- [ ] Negative keywords 적용 완료
- [ ] 즉시 제거 조건 적용 완료
- [ ] 조건부 제거 판정 완료

### 8.4 데이터베이스 상태
- [ ] `raw_reddit_posts`에 유효 포스트만 남음
- [ ] 제거된 포스트는 별도 테이블 또는 플래그로 관리 (선택)
- [ ] `pipeline_runs`에 정제 상태 기록

---

## 9. 실행 절차

### 9.1 샘플 추출
```sql
-- 각 키워드별 상위 10개 포스트 추출
SELECT 
    keyword,
    reddit_post_id,
    title,
    selftext,
    upvotes,
    num_comments,
    subreddit
FROM raw_reddit_posts
WHERE keyword = ?
ORDER BY upvotes DESC, num_comments DESC
LIMIT 10;

-- 각 포스트의 Top 1-2 댓글
SELECT 
    body,
    upvotes,
    author
FROM raw_reddit_comments
WHERE reddit_post_id = ?
ORDER BY upvotes DESC
LIMIT 2;
```

### 9.2 판정 프로세스
1. **포스트 단위 판정**
   - 즉시 제거 조건 체크 → 해당 시 DROP
   - 조건부 제거 조건 체크 → 대부분 DROP
   - 유지 조건 체크 → 해당 시 KEEP
   - 4대 주제별 핵심 질문 적용 → 매핑 가능 여부 확인

2. **키워드 단위 판정**
   - 키워드별 샘플 10개 판정 결과 집계
   - 오탐 비율 계산
   - 주제 일관성 평가
   - 구매/고장 비율 계산
   - 후보 조건 2개 이상 → DROP 확정

3. **최종 리스트 생성**
   - KEEP 키워드 리스트
   - DROP 키워드 리스트 (근거 포함)
   - REVIEW 키워드 리스트 (재검토 필요)

### 9.3 필터링 적용
1. Negative keywords 정규식 적용
2. 즉시 제거 조건 SQL WHERE 절 적용
3. 조건부 제거 판정 결과 반영
4. 키워드 삭제 확정 키워드의 모든 포스트 제거

---

## 10. 예상 결과물

### 10.1 키워드 최종 리스트
```
SPRING_RECIPES:
  KEEP: spring dinner ideas, easy spring meals, what to cook in spring, ...
  DROP: spring recipe book (구매 중심), spring recipe app (앱 추천)
  REVIEW: (최소화)

SPRING_KITCHEN_STYLING:
  KEEP: spring kitchen decor, kitchen spring refresh, ...
  DROP: spring kitchen fashion (패션 오탐)
  REVIEW: (최소화)

REFRIGERATOR_ORGANIZATION:
  KEEP: refrigerator organization, fridge organization tips, ...
  DROP: refrigerator repair (수리 중심), refrigerator buying guide (구매)
  REVIEW: (최소화)

VEGETABLE_PREP_HANDLING:
  KEEP: vegetable prep, how to prep vegetables, ...
  DROP: vegetable gardening (재배 중심), vegetable seeds (재배)
  REVIEW: (최소화)
```

### 10.2 DROP 키워드 근거
- **spring recipe book**: 샘플 10개 중 8개가 책 추천/구매 관련
- **refrigerator repair**: 샘플 10개 중 9개가 고장/수리 관련
- **vegetable gardening**: 샘플 10개 중 7개가 재배/가드닝 관련

### 10.3 포스트 필터링 룰
- Negative keywords 정규식 패턴
- SQL WHERE 절 조건
- Python 필터 함수

### 10.4 컷 비율 목표
- 포스트: 35% 제거 목표
- 키워드: 25% 제거 목표

---

## 11. 다음 단계 (analyze 단계 전)

정제 완료 후 `analyze` 단계로 진행:
- 정제된 포스트로 임베딩 생성
- HDBSCAN 클러스터링
- 클러스터별 특징어 추출
- 시계열 분석
