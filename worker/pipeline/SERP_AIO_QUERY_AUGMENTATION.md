# SerpAPI AI Overview 쿼리 증강 전략

## 배경

현재 단계에서는 단순 키워드("spring dinner ideas", "refrigerator organization" 등)로만 검색하여 AI Overview가 거의 나오지 않았습니다.

**원인:**
- Google AI Overview는 구체적이고 실제 질문 형태의 쿼리에 더 잘 반응
- 단순 키워드는 검색 결과는 나오지만 AI Overview 생성 기준을 충족하지 못함

**해결책:**
- Reddit 분석 결과를 활용하여 쿼리를 증강(augment)
- 실제 사용자 질문, 구체적 고민 포인트를 반영한 쿼리 생성

---

## 쿼리 증강 전략

### 1. Reddit 분석 결과 활용

#### 1.1 클러스터별 대표 질문 추출
Reddit 클러스터링 후 각 클러스터에서:
- 가장 많이 등장하는 질문 패턴 추출
- 실제 사용자 고민 포인트 파악
- 구체적인 "How-to", "What", "Why" 질문 식별

**예시:**
```
원본 키워드: "spring dinner ideas"
증강 쿼리: "What are easy spring dinner ideas for weeknight meals?"
증강 쿼리: "How do you plan spring dinner ideas for a family of four?"
증강 쿼리: "Best spring dinner ideas for meal prep on Sunday?"
```

#### 1.2 클러스터 특징어 조합
클러스터에서 추출한 키워드들을 조합하여 자연스러운 질문 생성:

**예시:**
```
원본 키워드: "refrigerator organization"
클러스터 키워드: ["meal prep", "leftovers", "drawers", "containers"]
증강 쿼리: "How to organize refrigerator for meal prep and leftovers?"
증강 쿼리: "Best refrigerator organization system using containers and drawers?"
```

#### 1.3 Reddit 댓글 인사이트 반영
댓글에서 자주 언급되는 구체적 팁/고민을 쿼리에 포함:

**예시:**
```
원본 키워드: "vegetable prep"
댓글 인사이트: "washing", "storage containers", "meal prep", "freshness"
증강 쿼리: "How to prep and store vegetables for meal prep to keep them fresh?"
증강 쿼리: "Best way to wash and store vegetables in containers?"
```

---

## 쿼리 증강 구현 방법

### 2.1 클러스터 기반 쿼리 생성

```python
def generate_augmented_queries(cluster_id: int, base_keyword: str) -> List[str]:
    """
    클러스터 분석 결과를 기반으로 증강 쿼리 생성
    
    Args:
        cluster_id: 클러스터 ID
        base_keyword: 원본 키워드
    
    Returns:
        증강된 쿼리 리스트
    """
    # 1. 클러스터 특징어 추출
    keywords = extract_cluster_keywords(cluster_id, top_n=5)
    
    # 2. 클러스터 대표 질문 추출
    questions = extract_cluster_questions(cluster_id, top_n=3)
    
    # 3. 쿼리 생성 패턴
    patterns = [
        f"What are {base_keyword} for {keywords[0]}?",
        f"How do you {base_keyword} with {keywords[1]}?",
        f"Best {base_keyword} for {keywords[2]}?",
        questions[0] if questions else None,
        questions[1] if len(questions) > 1 else None,
    ]
    
    # 4. 필터링 및 반환
    return [q for q in patterns if q and len(q) < 100]
```

### 2.2 LLM 기반 쿼리 증강

```python
def augment_query_with_llm(base_keyword: str, cluster_context: Dict) -> List[str]:
    """
    LLM을 사용하여 컨텍스트 기반 쿼리 증강
    
    Args:
        base_keyword: 원본 키워드
        cluster_context: 클러스터 컨텍스트 (키워드, 질문, 댓글 요약)
    
    Returns:
        증강된 쿼리 리스트
    """
    prompt = f"""
    Generate 3-5 Google search queries that would likely trigger AI Overview
    based on the following context:
    
    Base keyword: {base_keyword}
    Cluster keywords: {cluster_context['keywords']}
    Common questions: {cluster_context['questions']}
    
    Requirements:
    - Queries should be specific, question-based
    - Should include "how", "what", "best", "tips" when appropriate
    - Should be natural language that users would actually search
    - Each query should be 5-15 words
    
    Return as JSON array of strings.
    """
    
    # LLM 호출 (gpt-4o-mini)
    response = call_llm(prompt, schema={"queries": ["string"]})
    return response["queries"]
```

---

## 쿼리 증강 실행 시점

### 3.1 파이프라인 단계별 실행

```
1. collect (Reddit 수집)
   ↓
2. analyze (클러스터링, 키워드 추출)
   ↓
3. augment_queries (쿼리 증강) ← 새 단계 추가
   ↓
4. collect_serp_aio (증강된 쿼리로 AI Overview 수집)
   ↓
5. label (LLM 브리프 생성, 증강 쿼리 결과 포함)
```

### 3.2 쿼리 증강 모듈 구조

```
worker/pipeline/
  ├── query_augmentation.py  # 쿼리 증강 로직
  ├── collect_serp_aio.py     # 기존 수집 모듈 (증강 쿼리 지원)
  └── ...
```

---

## 쿼리 증강 예시

### 예시 1: SPRING_RECIPES

**원본 키워드:**
- "spring dinner ideas"

**Reddit 분석 결과:**
- 클러스터 키워드: ["weeknight", "family", "meal prep", "healthy", "quick"]
- 대표 질문: "What do you cook for spring weeknight dinners?"
- 댓글 인사이트: "meal prep on Sunday", "family of 4", "30 minutes"

**증강 쿼리:**
1. "What are easy spring dinner ideas for weeknight meals?"
2. "How do you meal prep spring dinners for a family?"
3. "Best quick spring dinner recipes under 30 minutes?"
4. "What do you cook for spring weeknight dinners?"
5. "Healthy spring dinner ideas for meal prep on Sunday?"

### 예시 2: REFRIGERATOR_ORGANIZATION

**원본 키워드:**
- "refrigerator organization"

**Reddit 분석 결과:**
- 클러스터 키워드: ["drawers", "containers", "meal prep", "leftovers", "zones"]
- 대표 질문: "How do you organize your refrigerator for meal prep?"
- 댓글 인사이트: "upper shelves for ready-to-eat", "drawers for vegetables"

**증강 쿼리:**
1. "How to organize refrigerator for meal prep and leftovers?"
2. "Best refrigerator organization system using containers and drawers?"
3. "What goes where when organizing refrigerator zones?"
4. "How do you organize your refrigerator for meal prep?"
5. "Refrigerator organization tips for upper shelves and drawers?"

### 예시 3: VEGETABLE_PREP_HANDLING

**원본 키워드:**
- "vegetable prep"

**Reddit 분석 결과:**
- 클러스터 키워드: ["washing", "storage", "containers", "freshness", "meal prep"]
- 대표 질문: "How do you prep vegetables to keep them fresh longer?"
- 댓글 인사이트: "paper towel method", "ice water bath", "airtight containers"

**증강 쿼리:**
1. "How to prep and store vegetables for meal prep to keep them fresh?"
2. "Best way to wash and store vegetables in containers?"
3. "How do you prep vegetables to keep them fresh longer?"
4. "Vegetable prep tips using paper towels and airtight containers?"
5. "What's the best method to prep vegetables for meal prep?"

---

## AI Overview 수집 전략

### 4.1 증강 쿼리 우선순위

1. **대표 질문 우선**: 클러스터에서 추출한 실제 질문 형태
2. **How-to 질문**: "How do you...", "How to..." 패턴
3. **Best/Tips 질문**: "Best way to...", "Tips for..." 패턴
4. **What 질문**: "What are...", "What do you..." 패턴

### 4.2 쿼리별 수집 제한

- 클러스터당 증강 쿼리: 3-5개
- 각 증강 쿼리로 AI Overview 수집
- AI Overview가 있는 쿼리만 클러스터에 연결

### 4.3 데이터 저장 구조

```sql
-- raw_serp_aio 테이블에 추가 필드 (선택사항)
ALTER TABLE raw_serp_aio ADD COLUMN IF NOT EXISTS cluster_id INTEGER;
ALTER TABLE raw_serp_aio ADD COLUMN IF NOT EXISTS base_keyword VARCHAR(200);
ALTER TABLE raw_serp_aio ADD COLUMN IF NOT EXISTS is_augmented BOOLEAN DEFAULT FALSE;
```

---

## 구현 우선순위

### Phase 1: 기본 증강 (현재)
- ✅ 단순 키워드로 샘플 수집 완료
- ✅ 적재 검증 완료

### Phase 2: 클러스터 기반 증강 (다음 단계)
- [ ] 클러스터링 완료 후
- [ ] 클러스터별 키워드/질문 추출
- [ ] 간단한 패턴 기반 쿼리 증강
- [ ] 증강 쿼리로 AI Overview 수집

### Phase 3: LLM 기반 증강 (향후)
- [ ] LLM을 사용한 컨텍스트 기반 쿼리 생성
- [ ] 더 자연스럽고 효과적인 쿼리 생성
- [ ] AI Overview 확률 높은 쿼리 자동 생성

---

## 예상 효과

### 현재 (단순 키워드)
- AI Overview 확률: ~0-20%
- 4개 쿼리 중 0개 AVAILABLE

### 증강 후 (예상)
- AI Overview 확률: ~40-60%
- 클러스터당 3-5개 증강 쿼리
- 각 클러스터당 1-3개 AVAILABLE 예상

---

## 참고

- Google AI Overview는 구체적이고 실제 질문 형태의 쿼리에 더 잘 반응
- Reddit 분석 결과를 활용하면 실제 사용자 관심사와 일치하는 쿼리 생성 가능
- 증강 쿼리는 Evidence Pack 구성에도 유용 (SERP AIO + Reddit 데이터 결합)
