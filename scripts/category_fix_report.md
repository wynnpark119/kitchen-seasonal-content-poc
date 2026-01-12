# 카테고리 분류 로직 수정 보고서

## 문제 분석

### [1] assign_post_to_category() 함수 로직 분석

**파일**: `worker/pipeline/tfidf_clustering.py` 라인 55-90 (수정 전)

**기존 로직의 문제점**:

1. **subreddit 정보 미사용** (라인 55-90)
   - 함수 시그니처에 `subreddit` 파라미터가 없음
   - subreddit 정보를 전혀 고려하지 않음

2. **키워드 매칭이 너무 느슨함** (라인 76-86)
   - `post_lower.count(kw)` 사용으로 부분 문자열 매칭
   - "my", "me" 같은 stopword도 매칭 가능
   - 예: "my girlfriend" → "my" 매칭 → SPRING_RECIPES로 잘못 분류

3. **기본값 할당 문제** (라인 89-90)
   - 매칭 실패 시 무조건 `SPRING_RECIPES` 반환
   - AITA, 관계 상담 포스트도 기본값으로 SPRING_RECIPES에 포함됨

**왜 AITA/관계 포스트가 포함되는가**:
- "my", "me" 같은 단어가 CATEGORY_KEYWORDS에 포함되어 있지 않지만
- 텍스트에 "my", "me"가 많이 나타나면 다른 키워드와 함께 카운트되어
- 점수가 가장 높은 카테고리로 분류될 수 있음
- 또는 매칭 실패 시 기본값으로 SPRING_RECIPES 할당

## 수정 사항

### [2] 수정된 로직

**파일**: `worker/pipeline/tfidf_clustering.py` 라인 24-150 (수정 후)

**주요 변경사항**:

1. **subreddit 기반 필터링 추가** (라인 24-42)
   - `CATEGORY_SUBREDDITS`: 각 카테고리별 허용 subreddit 목록 정의
   - 요리/주방 관련 subreddit만 허용 (예: cooking, recipes, food, baking 등)

2. **제외 subreddit 목록 추가** (라인 67-73)
   - `EXCLUDED_SUBREDDITS`: 명시적으로 제외할 subreddit 목록
   - AITA, 관계 상담, 일반 토론 subreddit 제외

3. **함수 시그니처 변경** (라인 86-87)
   - `subreddit` 파라미터 추가 (필수)
   - 반환 타입: `Optional[str]` (매칭 실패 시 None 반환)

4. **로직 개선** (라인 99-150)
   - subreddit이 없으면 None 반환 (라인 100-101)
   - 제외 subreddit 체크 (라인 105-107)
   - subreddit 기반 매칭 우선 (라인 109-115)
   - 키워드는 보조 신호로만 사용 (라인 121-127, 129-140)
   - 단어 경계 고려한 키워드 매칭 (라인 134-136)
   - 기본값 할당 제거 (None 반환)

5. **호출부 수정** (라인 343-361)
   - DB 쿼리에 `subreddit` 컬럼 추가
   - `assign_post_to_category()` 호출 시 subreddit 전달
   - None 반환 시 스킵 (기본값 할당 금지)

## 검증 방법

### [3] 검증 스크립트

**파일**: `scripts/test_category_assignment.py`

**검증 항목**:
1. 각 topic_category별 포스트 수
2. 각 카테고리별 상위 10개 샘플 포스트 출력
3. subreddit 분포 확인
4. 주제 일관성 검증 (문제가 있는 subreddit 확인)

**실행 방법**:
```bash
python3 scripts/test_category_assignment.py
```

## 다음 단계

### [4] 검증 PASS 후 클러스터링 재실행

검증이 PASS되면:
1. 기존 클러스터 데이터 삭제 (선택사항)
2. `run_tfidf_clustering()` 재실행
3. 결과 검증

**주의사항**:
- 클러스터링 알고리즘은 수정하지 않음
- 임베딩/GPT/SERP 단계로 넘어가지 않음
- 데이터 의미 정합성 확보가 최우선

## 수정된 코드 위치

1. **카테고리별 subreddit 목록**: `worker/pipeline/tfidf_clustering.py` 라인 24-42
2. **제외 subreddit 목록**: 라인 67-73
3. **assign_post_to_category 함수**: 라인 86-150
4. **호출부 (DB 쿼리)**: 라인 320-326
5. **호출부 (카테고리 할당)**: 라인 343-361

## 예상 효과

1. ✅ AITA, 관계 상담 포스트가 SPRING_RECIPES에 포함되지 않음
2. ✅ 요리/주방 관련 subreddit의 포스트만 각 카테고리에 할당됨
3. ✅ 매칭 실패 시 기본값 할당 없이 스킵됨
4. ✅ 주제 일관성이 크게 향상됨
