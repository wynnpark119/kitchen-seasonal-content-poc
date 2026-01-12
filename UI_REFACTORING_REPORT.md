# Streamlit 대시보드 UI 최종 스펙 수정 보고서

작업 일시: 2024년
작업 목표: 최종 화면 스펙 기준으로 UI 수정 및 Master Topics 출력 문제 해결

---

## (A) 수정된 파일 경로 리스트

1. **web/app.py**
   - 탭 라벨 변경
   - 각 탭 상단에 헤더 추가

2. **web/views/master_topics.py**
   - Master Topics 파싱 로직 추가 (`parse_master_topics()` 함수)
   - 구조화된 렌더링으로 변경
   - 카테고리별 expander 사용

3. **web/views/trend_explorer.py**
   - 함수 docstring 업데이트
   - 에러 메시지 개선

4. **web/views/clustering_results.py**
   - 함수 docstring 업데이트
   - 에러 메시지 개선

---

## (B) UI 변경 요약

### 1. 탭 라벨 변경

**Before:**
- "🎯 Clustering Results"
- "📈 AIO Overview"
- "🎯 Master Topics"

**After:**
- "🧠 Reddit 토픽 분석"
- "🔎 구글 AI 검색 결과 분석"
- "🏠 LG전자 HS 마스터 토픽 제안"

### 2. 탭 상단 헤더 추가

각 탭 컨테이너 시작 부분에 `st.header()` 추가:

```python
with tab1:
    st.header("🧠 Reddit 토픽 분석")
    render_clustering_results()

with tab2:
    st.header("🔎 구글 AI 검색 결과 분석")
    render_trend_explorer()

with tab3:
    st.header("🏠 LG전자 HS 마스터 토픽 제안")
    render_master_topics()
```

### 3. Master Topics 렌더링 개선

**Before:**
- JSON에서 불러온 마크다운을 그대로 `st.markdown()`으로 표시
- 구분선(`========`)이 포함되어 가독성 저하
- 카테고리별로 구조화되지 않음

**After:**
- `parse_master_topics()` 함수로 마크다운 파싱
- 카테고리별 `st.expander()` 사용
- 각 항목을 구조화된 형태로 표시:
  - 제목: `**1. 제목**`
  - Why now: `**Why now:** 내용`
  - 항목 간 구분선

### 4. 에러 메시지 개선

- 데이터가 없을 때 단순 "Not available" 대신 구체적인 경고 메시지 표시
- 파싱 실패 시 원문 일부만 표시 (최대 500자)

---

## (C) Master Topics 파싱/렌더링 로직 설명

### 핵심 함수: `parse_master_topics()`

**위치:** `web/views/master_topics.py`

**입력:**
- `markdown_text` (str): 마크다운 형식의 텍스트

**출력:**
- `List[Dict]`: 각 항목은 `{'title': str, 'why_now': str}` 형태

**파싱 로직:**
1. 줄 단위로 텍스트 분리
2. 번호 패턴 매칭 (`1) **제목**` 또는 `1) 제목`)
3. "Why now:" 패턴 매칭 (다양한 형식 지원)
4. Why now 섹션 내 텍스트 수집
5. 다음 번호 항목이 나오면 이전 항목 저장
6. 마크다운 제거 (`**`, `` ` `` 등)

**지원하는 마크다운 형식:**
- `1) **제목**`
- `1) 제목`
- `- **Why now:** 내용`
- `**Why now:** 내용`
- `Why now: 내용`

**렌더링 방식:**
```python
for item in parsed_items:
    st.markdown(f"**{item_idx}. {item['title']}**")
    st.markdown(f"**Why now:** {item['why_now']}")
    st.markdown("---")
```

**파싱 실패 시:**
- 경고 메시지 표시
- 원문 일부만 표시 (최대 500자)
- 전체 덤프 방지

---

## (D) 스크린샷 확인 포인트

### 탭 1: Reddit 토픽 분석
- ✅ 탭 라벨: "🧠 Reddit 토픽 분석"
- ✅ 상단 헤더: "🧠 Reddit 토픽 분석" 표시
- ✅ 클러스터링 결과가 카테고리별로 표시되는지 확인

### 탭 2: 구글 AI 검색 결과 분석
- ✅ 탭 라벨: "🔎 구글 AI 검색 결과 분석"
- ✅ 상단 헤더: "🔎 구글 AI 검색 결과 분석" 표시
- ✅ 통계 요약 (Total Queries, Available, Not Available)
- ✅ 번호가 달린 리스트 (1., 2., 3., ...)
- ✅ Available/Not Available 태그 표시
- ✅ More 버튼으로 추가 항목 로드

### 탭 3: LG전자 HS 마스터 토픽 제안
- ✅ 탭 라벨: "🏠 LG전자 HS 마스터 토픽 제안"
- ✅ 상단 헤더: "🏠 LG전자 HS 마스터 토픽 제안" 표시
- ✅ 1초 로딩 표시
- ✅ 4개 카테고리별 expander:
  - SPRING_RECIPES
  - REFRIGERATOR_ORGANIZATION
  - VEGETABLE_PREP_HANDLING
  - SPRING_KITCHEN_STYLING
- ✅ 각 카테고리 내부:
  - 5개 항목이 구조화되어 표시
  - 각 항목: "**1. 제목**" + "**Why now:** 내용"
  - 항목 간 구분선
- ✅ JSON 덤프 형태가 아닌 깔끔한 구조화된 형태
- ✅ 카테고리별로 섹션이 명확히 분리됨

---

## 검증 체크리스트

### 탭 라벨
- [x] "🧠 Reddit 토픽 분석"
- [x] "🔎 구글 AI 검색 결과 분석"
- [x] "🏠 LG전자 HS 마스터 토픽 제안"

### 탭 헤더
- [x] 각 탭 클릭 시 상단에 헤더 표시
- [x] 헤더 텍스트가 탭 라벨과 일치

### Master Topics
- [x] 4개 topic_category가 섹션으로 분리
- [x] 각 섹션에서 5개 항목이 구조화되어 표시
- [x] 제목과 Why now가 줄바꿈되어 표시
- [x] 내용이 없으면 "Not available" 표시
- [x] JSON 덤프 형태가 아닌 깔끔한 구조화된 형태

### AIO Overview
- [x] 상단 헤더 표시
- [x] 통계 요약 표시
- [x] 번호가 달린 리스트
- [x] Available/Not Available 태그
- [x] More 버튼 동작

---

## 추가 개선 사항

1. **파싱 견고성 향상**
   - 다양한 마크다운 형식 지원
   - 파싱 실패 시 graceful fallback

2. **에러 처리 개선**
   - 데이터 없을 때 구체적인 메시지
   - 파싱 실패 시 원문 일부만 표시

3. **가독성 향상**
   - 카테고리별 expander 사용
   - 항목 간 구분선
   - 마크다운 형식 유지하면서 구조화

---

## 결론

최종 화면 스펙 기준으로 UI를 수정하고, Master Topics 출력 문제를 해결했습니다. 주요 변경 사항:

1. **탭 라벨 변경**: 스펙에 맞게 한글 라벨로 변경
2. **헤더 추가**: 각 탭 상단에 명확한 헤더 표시
3. **Master Topics 구조화**: JSON 덤프 형태에서 구조화된 형태로 변경
4. **파싱 로직**: 마크다운을 파싱하여 제목과 Why now를 분리

이제 대시보드가 최종 스펙에 맞게 깔끔하고 구조화된 형태로 표시됩니다.
