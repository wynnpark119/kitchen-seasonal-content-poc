# Reddit 데이터 프루닝 결과 요약

## 현재 상태

**데이터베이스 상태:**
- 총 키워드: 100개 (config.py 기준)
- 실제 수집된 포스트: 1개 ("spring dinner ideas")
- 평가된 포스트: 1개

**참고:** 실제 프루닝을 수행하려면 각 키워드별로 최소 10개 이상의 포스트가 수집되어야 합니다.

---

## 프루닝 규칙 요약

### 1. 포스트 즉시 제거(Kill) 조건

#### 구매/추천/비교
- 패턴: `buy|purchase|price|cost|affordable|cheap|worth it|recommend|review|comparison|vs|which one|better|best brand`
- 예시: "Which refrigerator should I buy?", "Is this worth it?"

#### 고장/수리/AS
- 패턴: `not cooling|broken|repair|error code|warranty|compressor|ice maker|defrost|leaking|not working`
- 예시: "My refrigerator is not cooling", "Ice maker repair cost"

#### 오탐 방지
- `spring break|spring mattress|coil spring|engine spring` (spring 오탐)
- `hair styling|fashion styling|nail styling` (styling 오탐)
- `vegetable gardening|vegetable planting|vegetable seeds` (vegetable 오탐)

#### 브랜드/모델 중심
- 패턴: `model|spec|Samsung|LG|Whirlpool|KitchenAid|GE|Bosch`
- 예시: "Samsung RF28R7351SG Review"

### 2. 조건부 제거 조건

- 정보 밀도 낮음: 본문 50자 미만
- 댓글 거의 없음 + 질문 막연함: 댓글 0~1개 + 본문 100자 미만 + "any tips?" 수준
- 키워드 억지 매칭: 제목만 키워드, 본문 무관

### 3. 유지(Keep) 조건

- 댓글에 경험 공유/토론 존재: 댓글 3개 이상 또는 상위 댓글 upvotes 10 이상
- 실제 생활자 고민이 명확: "how do you", "what do you", "best way to" + 본문 100자 이상
- 계절/봄 맥락 또는 라이프스타일 맥락 분명
- 4대 주제 중 하나로 자연스럽게 매핑 가능

### 4. 키워드 삭제 규칙

**삭제 후보 조건 (하나라도 해당):**
1. 오탐/제외 대상 50% 이상
2. 주제 분산 (공통점 부족)
3. 구매/고장/AS 주류 (50% 이상)

**삭제 확정:** 후보 조건 2개 이상

---

## 4대 주제별 유지 핵심 질문

### SPRING_RECIPES
**질문:** "이 포스트로 블로그 글 1편을 쓸 수 있는가?"
- 봄 제철 재료 활용법
- 가벼운/건강한 식단 맥락
- 가족/혼밥/주말 요리 맥락

### SPRING_KITCHEN_STYLING
**질문:** "주방 분위기/연출을 왜/어떻게 바꾸는지 드러나는가?"
- 주방 인테리어/데코 아이디어
- 봄 분위기 연출(컬러, 식기, 소품)
- 홈 파티/테이블 세팅 맥락

### REFRIGERATOR_ORGANIZATION
**질문:** "정리 원칙/루틴/보관 고민이 드러나는가? (고장/AS는 제외)"
- 냉장고 정리/보관 노하우
- 계절 식재료 보관법
- 정리 루틴/공간 활용 팁

### VEGETABLE_PREP_HANDLING
**질문:** "요리 전 손질/세척/보관의 헷갈림 포인트인가? (가드닝 제외)"
- 야채 세척/손질/보관 팁
- 미리 손질해두는 방법
- 신선도 유지 팁

---

## Negative Keywords (정규식 패턴)

### 구매/비교
```regex
\b(buy|purchase|price|cost|affordable|cheap|expensive|worth it|recommend|review|comparison|vs|which one|better|best brand|where to buy|deal|sale|discount)\b
```

### 고장/수리/AS
```regex
\b(not cooling|broken|repair|error code|warranty|compressor|ice maker|defrost|leaking|not working|stopped|faulty|malfunction|service|technician|fix|damaged)\b
```

### 오탐 방지
```regex
\b(spring break|spring mattress|coil spring|engine spring|spring water|hair styling|fashion styling|nail styling|makeup styling|vegetable gardening|vegetable planting|vegetable seeds|vegetable growing)\b
```

### 브랜드/모델
```regex
\b(model|spec|specification|Samsung|LG|Whirlpool|KitchenAid|GE|Bosch|Maytag|Frigidaire)\b
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

### 판정 분류
- **KEEP:** 명확히 유지 (70~80%)
- **DROP:** 명확히 제거 (20~30%)
- **REVIEW:** 애매한 경우 (최소화, 5% 이하)

---

## 예상 DROP 키워드 (오탐 패턴 기반)

### SPRING_RECIPES
- ❌ `spring recipe book` - 책 추천/구매 중심
- ❌ `spring recipe app` - 앱 추천
- ❌ `spring recipe subscription` - 구독 서비스
- ❌ `spring recipe meal kit` - 배송 서비스

### SPRING_KITCHEN_STYLING
- ❌ `spring kitchen fashion` - 패션 오탐
- ❌ `spring kitchen hair styling` - 헤어 스타일링
- ❌ `spring kitchen makeup` - 메이크업
- ❌ `spring kitchen furniture store` - 가구 구매

### REFRIGERATOR_ORGANIZATION
- ❌ `refrigerator repair` - 수리 중심
- ❌ `refrigerator not cooling` - 고장
- ❌ `refrigerator warranty` - 보증/AS
- ❌ `refrigerator replacement` - 교체
- ❌ `refrigerator buying guide` - 구매
- ❌ `refrigerator reviews` - 제품 리뷰

### VEGETABLE_PREP_HANDLING
- ❌ `vegetable gardening` - 재배
- ❌ `vegetable planting` - 재배
- ❌ `vegetable seeds` - 재배
- ❌ `vegetable growing` - 재배
- ❌ `vegetable fertilizer` - 재배
- ❌ `vegetable soil` - 재배

---

## 정제 완료 조건 (analyze 단계 전)

### 데이터 품질
- [ ] 각 키워드별 최소 10개 이상 유효 포스트
- [ ] 오탐/노이즈 포스트 제거 완료
- [ ] 4대 주제별로 최소 1개 키워드 이상 유지

### 키워드 정제
- [ ] DROP 키워드 제거 완료
- [ ] REVIEW 키워드 판정 완료 (KEEP 또는 DROP 결정)
- [ ] 최종 키워드 리스트 확정

### 포스트 필터링
- [ ] Negative keywords 적용 완료
- [ ] 즉시 제거 조건 적용 완료
- [ ] 조건부 제거 판정 완료

### 컷 비율 달성
- [ ] 포스트 30~40% 제거 목표 달성
- [ ] 키워드 20~30% 제거 목표 달성

---

## 실행 방법

### 1. 샘플 추출 및 판정
```python
from worker.pipeline.pruning import prune_keywords

results = prune_keywords()
```

### 2. 결과 확인
```python
# KEEP 키워드
for item in results["keep"]:
    print(f"KEEP: {item['keyword']} - {item['reason']}")

# DROP 키워드
for item in results["drop"]:
    print(f"DROP: {item['keyword']} - {item['reason']}")
```

### 3. 필터링 적용
```sql
-- Negative keywords 적용
DELETE FROM raw_reddit_posts
WHERE 
    title ~* '(buy|purchase|price|recommend|repair|broken|not cooling)' 
    OR body ~* '(buy|purchase|price|recommend|repair|broken|not cooling)';

-- DROP 키워드 제거
DELETE FROM raw_reddit_posts
WHERE keyword IN (
    'spring recipe book',
    'refrigerator repair',
    'vegetable gardening'
    -- ... DROP 키워드 리스트
);
```

---

## 다음 단계

정제 완료 후:
```bash
python worker/run_pipeline.py --mode=analyze
```

이 단계에서:
- 정제된 포스트로 임베딩 생성
- HDBSCAN 클러스터링
- 클러스터별 특징어 추출
- 시계열 분석
