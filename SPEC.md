# SPEC.md - Kitchen Seasonal Content POC

## 1. 프로젝트 개요

### 1.1 프로젝트 배경과 문제 정의

북미 시장의 키친 라이프스타일 콘텐츠 기획 시, 계절성과 사용자 니즈를 정확히 파악하는 것이 핵심 과제다. 기존 방식은 주관적 판단이나 제한된 데이터 소스에 의존하여, 실제 검색 트렌드와 커뮤니티 반응을 반영하지 못하는 한계가 있다.

본 PoC는 Reddit, Google SERP AI Overview, Google Search Console 데이터를 통합 분석하여, 봄 시즌에 특화된 키친 라이프스타일 콘텐츠 주제를 데이터 기반으로 발굴하는 시스템을 구축한다.

### 1.2 왜 "구매/가전"이 아니라 "키친 라이프스타일"인가

구매/가전 카테고리는 제품 중심의 마케팅 접근이지만, 본 프로젝트는 사용자의 실제 행동과 니즈를 이해하는 것이 목적이다. 키친 라이프스타일은 다음과 같은 이유로 더 적합하다:

- **행동 기반 인사이트**: 레시피, 정리법, 스타일링 등 실제 행동 패턴을 반영
- **계절성 명확**: 봄 제철 재료, 봄 분위기 연출 등 계절적 맥락이 강함
- **커뮤니티 신호 강함**: Reddit에서 활발히 공유되는 주제들이 주로 라이프스타일 영역
- **콘텐츠 기획 직결**: 블로그/소셜 콘텐츠로 바로 활용 가능한 주제 발굴

가전/도구는 "배경 맥락(context)"으로만 취급하며, 직접적인 주제로는 다루지 않는다.

### 1.3 PoC 범위와 명확한 제외 범위

#### 포함 범위
- 4개 핵심 주제 카테고리: 봄 레시피, 봄 주방 스타일링, 냉장고 정리법, 야채 손질법
- Reddit 데이터 수집 및 분석 (키워드별 최대 1,000개 포스트)
- Google SERP AI Overview 1회 스냅샷 수집
- Google Search Console CSV 업로드 및 분석
- 클러스터링 기반 주제 발굴
- LLM 기반 Q&A brief 생성
- Streamlit 대시보드 제공

#### 제외 범위
- 실시간 데이터 수집 (배치 기반만 지원)
- 벡터 DB 사용 (Postgres에 직접 저장)
- 다국어 지원 (영어 데이터, 한국어 UI만)
- 가전/도구를 직접 주제로 하는 분석
- 문서 단위 LLM 호출 (클러스터 단위만)
- 자동화된 콘텐츠 생성 (주제 발굴까지만)

---

## 2. 전체 시스템 아키텍처 개요

### 2.1 데이터 흐름

```
[데이터 소스]
    ↓
[Worker: 데이터 수집]
    ├─ Reddit API → Raw 데이터 저장
    ├─ SerpAPI (SERP AIO) → Raw 데이터 저장
    └─ GSC CSV 업로드 → Raw 데이터 저장
    ↓
[Worker: 데이터 정제]
    ├─ 필터링 (질문형/How-to/아이디어성)
    ├─ 중복 제거
    ├─ 언어/길이/노이즈 처리
    └─ 월 단위 집계
    ↓
[Worker: 분석 파이프라인]
    ├─ 임베딩 생성
    ├─ HDBSCAN 클러스터링
    ├─ 클러스터 후처리 (특징어 추출)
    ├─ Intent Taxonomy 매핑
    └─ 시계열 트렌드 분석
    ↓
[Worker: LLM 호출]
    ├─ 클러스터 단위 Q&A brief 생성
    └─ Evidence Pack 생성
    ↓
[PostgreSQL]
    ├─ Raw 데이터 테이블
    ├─ 정제 데이터 테이블
    ├─ 클러스터 테이블
    ├─ LLM 결과 테이블
    └─ 시계열 집계 테이블
    ↓
[Web: Streamlit 대시보드]
    ├─ Raw 데이터 검증 화면
    ├─ 클러스터 + 시계열 분석 화면
    └─ 콘텐츠 주제 발굴 화면
```

### 2.2 컴포넌트 역할 구분

#### Worker (데이터 수집/분석 파이프라인)
- Reddit API를 통한 데이터 수집
- SerpAPI를 통한 SERP AI Overview 수집
- GSC CSV 파싱 및 저장
- 데이터 정제 및 전처리
- 임베딩 생성 및 클러스터링
- LLM 호출 및 결과 저장
- 배치 실행 또는 스케줄링 지원

#### Web (Streamlit 대시보드)
- PostgreSQL에서 분석 결과 조회
- Raw 데이터 검증 및 필터링
- 클러스터 시각화
- 시계열 트렌드 차트
- 콘텐츠 주제 발굴 결과 표시
- Evidence Pack 표시

#### Common (공용 모듈)
- PostgreSQL 연결 관리
- 환경 변수 관리
- 공용 유틸리티 함수
- 데이터 모델 정의

### 2.3 Railway 배포 환경 기준 운영 구조

- **Streamlit 서비스**: Railway에서 자동 배포, `$PORT` 환경 변수 사용
- **Worker 서비스**: 별도 서비스로 배포 또는 스케줄러 실행
- **PostgreSQL**: Railway PostgreSQL 플러그인 사용, `DATABASE_URL` 자동 주입
- **환경 변수**: Railway 대시보드에서 관리 (API 키, LLM 키 등)

---

## 3. 데이터 소스 및 수집 범위 정의

### 3.1 Reddit 데이터

#### 키워드 전략
4개 핵심 주제 카테고리에 맞춘 키워드 세트를 구성한다:

**봄 레시피 (Spring Recipes)**
- spring recipes, spring cooking, spring meal prep
- spring vegetables, seasonal cooking, light spring meals
- spring dinner ideas, spring lunch recipes

**봄 주방 스타일링 (Spring Kitchen Styling)**
- spring kitchen decor, spring kitchen styling
- kitchen spring refresh, spring table setting
- spring home decor kitchen

**냉장고 정리법 (Refrigerator Organization)**
- refrigerator organization, fridge organization
- refrigerator storage, fridge cleaning tips
- refrigerator meal prep organization

**야채 손질법 (Vegetable Prep & Handling)**
- vegetable prep, vegetable storage
- how to prep vegetables, vegetable cleaning
- meal prep vegetables, vegetable handling

#### 수집 규칙
- 키워드별 최대 1,000개 포스트 상한
- 기간 제한 없음 (여러 년치 포함 가능)
- 반응 기반 우선순위:
  1. 업보트 수 (upvotes) 내림차순
  2. 댓글 수 (comments) 내림차순
  3. 최신순 (created_utc)
- 각 포스트당 인기 댓글 Top 3개만 수집
  - 댓글의 업보트 수 기준
  - 댓글 본문과 업보트 수 저장

#### 저장 데이터 구조
- 포스트: title, selftext, author, created_utc, upvotes, num_comments, url, subreddit
- 댓글: body, author, created_utc, upvotes (포스트별 Top 3)

### 3.2 Google SERP AI Overview

#### 수집 목적
- AI Overview에서 다루는 질문 구조 파악
- 키워드별 포화도 참고 지표로 활용
- 사용자 질문 패턴 이해

#### 수집 방식
- SerpAPI를 통한 1회 스냅샷 수집
- 기간 필터는 중요하지 않음
- AI Overview가 존재하는 키워드만 수집

#### 저장 데이터 구조
- 키워드, AI Overview 텍스트, 질문 리스트, 출처 URL

### 3.3 Google Search Console

#### CSV 스키마 개요
- 기간: 작년 1월 1일 ~ 12월 31일 (1년 고정)
- 입력 방식: CSV 파일 업로드
- 필수 컬럼:
  - Query (검색 쿼리)
  - Date (날짜)
  - Impressions (노출 수)
  - Clicks (클릭 수)
  - CTR (클릭률)
  - Position (평균 순위)

#### 활용 지표
- **Impressions**: 검색량 추정 및 트렌드 파악
- **Clicks**: 실제 관심도 측정
- **CTR**: 경쟁 강도 추정
- **Position**: 검색 결과 노출 위치

#### 월 단위 집계
- Date를 기준으로 월별로 집계
- Query별 월별 Impressions, Clicks, CTR, Position 평균 계산

---

## 4. 데이터 정제 및 전처리 규칙

### 4.1 질문형/How-to/아이디어성 콘텐츠 필터링 기준

#### 포함 대상
- 질문형: "How to...", "What is...", "Why...", "When...", "Where..."
- How-to: 단계별 가이드, 튜토리얼 형식
- 아이디어성: "Ideas for...", "Tips for...", "Ways to...", "Best..."
- 요청형: "Looking for...", "Need help with..."

#### 제외 대상
- 단순 링크 공유 (selftext가 비어있거나 URL만 있는 경우)
- 광고/프로모션 성격의 포스트
- 개인 일기/후기만 있는 포스트 (일반화 가능한 인사이트 없음)

### 4.2 중복 제거 기준

- **제목 유사도**: Levenshtein 거리 기반, 80% 이상 유사 시 중복으로 간주
- **본문 유사도**: 임베딩 코사인 유사도 0.95 이상 시 중복으로 간주
- **URL 중복**: 동일 URL은 자동 제거
- **우선순위**: 업보트 수가 높은 포스트 우선 유지

### 4.3 언어/길이/노이즈 처리

#### 언어 필터링
- 영어만 포함 (langdetect 또는 언어 감지 라이브러리 사용)
- 비영어 콘텐츠는 자동 제외

#### 길이 필터링
- 최소 길이: 제목 10자 이상, 본문 50자 이상
- 최대 길이: 본문 10,000자 초과 시 제외 (너무 긴 경우)

#### 노이즈 처리
- HTML 태그 제거
- 특수 문자 정규화
- URL 제거 (분석 대상에서)
- 이모지/이모티콘은 유지 (의미 있는 신호일 수 있음)
- Reddit 마크다운 형식 정리 (코드 블록, 인용 등)

### 4.4 Reddit 데이터의 created_at 정규화 및 월 단위 집계

#### 시간 정규화
- `created_utc` (Unix timestamp)를 UTC 기준으로 변환
- 타임존은 UTC 기준으로 통일
- 월 단위로 그룹화: YYYY-MM 형식

#### 월 단위 집계 방식
- 포스트 수: 월별 포스트 개수
- 평균 업보트: 월별 평균 업보트 수
- 평균 댓글 수: 월별 평균 댓글 수
- 총 업보트: 월별 총 업보트 수
- 총 댓글 수: 월별 총 댓글 수

#### 트렌드 계산
- 전월 대비 증감률 계산
- 계절성 패턴 파악 (봄 시즌 집중도)

---

## 5. 임베딩 및 클러스터링 전략

### 5.1 임베딩 모델 선택 이유

- **모델**: sentence-transformers의 `all-MiniLM-L6-v2` 또는 `all-mpnet-base-v2`
- **선택 이유**:
  - 영어 텍스트에 최적화
  - 문장 단위 의미 이해
  - 계산 비용 대비 성능 우수
  - 오픈소스로 비용 부담 없음

#### 임베딩 생성 규칙
- 제목 + 본문을 결합하여 하나의 텍스트로 처리
- 최대 길이 제한: 512 토큰 (모델 제한)
- 댓글은 별도 임베딩 생성하지 않음 (포스트 중심)

### 5.2 HDBSCAN 선택 이유

- **알고리즘**: HDBSCAN (Hierarchical Density-Based Spatial Clustering)
- **선택 이유**:
  - 클러스터 수를 사전에 지정하지 않아도 됨
  - 노이즈 포인트 자동 식별
  - 밀도 기반으로 자연스러운 클러스터 형성
  - 다양한 크기의 클러스터 처리 가능

#### HDBSCAN 파라미터
- `min_cluster_size`: 최소 클러스터 크기 (기본값: 5)
- `min_samples`: 코어 포인트 최소 샘플 수 (기본값: 3)
- `metric`: 'euclidean' 또는 'cosine'
- `cluster_selection_epsilon`: 클러스터 선택 임계값

### 5.3 Noise 처리 방식 및 로그 지표

#### Noise 처리
- HDBSCAN이 `-1`로 분류한 포인트는 "noise"로 처리
- Noise는 별도 테이블에 저장하되, 분석 대상에서 제외
- Noise 비율을 로그로 기록

#### 로그 지표
- 총 포스트 수
- 클러스터 수
- Noise 포인트 수
- Noise 비율 (%)
- 평균 클러스터 크기
- 최대/최소 클러스터 크기

### 5.4 Centroid 기준 대표 샘플 선정 규칙

#### 대표 샘플 선정
- 클러스터 내 모든 포인트의 임베딩 평균을 centroid로 계산
- Centroid와 코사인 유사도가 가장 높은 포스트를 대표 샘플로 선정
- 대표 샘플은 LLM 입력에 사용

#### 대체 규칙
- 대표 샘플이 없을 경우, 업보트 수가 가장 높은 포스트를 대표 샘플로 사용

### 5.5 클러스터 수 상한 및 우선순위 기준

#### 클러스터 수 상한
- 명시적 상한은 없음 (HDBSCAN이 자동 결정)
- 다만, 너무 많은 클러스터가 생성될 경우 파라미터 조정

#### 우선순위 기준
1. **클러스터 크기**: 큰 클러스터 우선
2. **평균 업보트**: 높은 반응 클러스터 우선
3. **최근성**: 최근 포스트 비율이 높은 클러스터 우선
4. **GSC 연관성**: GSC 데이터와 연관된 키워드가 많은 클러스터 우선

---

## 6. Intent Taxonomy (대주제 4개 기준, 고정)

모든 클러스터는 아래 4개 중 하나의 대주제 카테고리에 반드시 매핑된다. 매핑은 LLM이 수행하며, 명확하지 않은 경우 규칙 기반으로 보완한다.

### ① Spring Recipes (봄 레시피)

#### 정의
봄 제철 재료를 활용한 레시피, 가벼운 홈쿡, 건강한 식단, 가족/혼밥/주말 요리 맥락의 콘텐츠

#### 포함 키워드 예시
- spring vegetables, seasonal recipes, light meals
- healthy spring cooking, meal prep spring
- family dinner spring, weekend cooking

#### 제외
- 가전 제품 사용법 (레시피 자체가 목적이 아닌 경우)
- 단순 제품 리뷰

### ② Spring Kitchen Styling (봄 주방 스타일링)

#### 정의
주방 인테리어/데코 아이디어, 봄 분위기 연출(컬러, 식기, 소품), 홈 파티, 테이블 세팅

#### 포함 키워드 예시
- kitchen decor spring, spring table setting
- kitchen refresh, spring home styling
- party setup spring, seasonal decor

#### 제외
- 가전 제품 구매 가이드 (스타일링이 목적이 아닌 경우)
- 단순 제품 추천

### ③ Refrigerator Organization (냉장고 정리법)

#### 정의
냉장고 정리/보관 노하우, 계절 식재료 보관, 정리 루틴, 공간 활용

#### 포함 키워드 예시
- fridge organization, refrigerator storage
- meal prep organization, fridge cleaning
- food storage tips, organization system

#### 제외
- 냉장고 구매 가이드 (정리법이 목적이 아닌 경우)
- 단순 제품 리뷰

### ④ Vegetable Prep & Handling (야채 손질법)

#### 정의
야채 세척/손질/보관, 미리 손질해두는 방법, 신선도 유지 팁

#### 포함 키워드 예시
- vegetable prep, vegetable storage
- how to prep vegetables, vegetable cleaning
- meal prep vegetables, fresh vegetable tips

#### 제외
- 야채 구매 가이드 (손질법이 목적이 아닌 경우)
- 단순 제품 추천

### 가전/도구의 역할

가전/도구는 항상 "배경 맥락(context)"으로만 취급한다. 예를 들어:
- "인스턴트팟으로 만드는 봄 레시피" → Spring Recipes (인스턴트팟은 맥락)
- "에어프라이어 냉장고 정리법" → Refrigerator Organization (에어프라이어는 맥락)

---

## 7. 클러스터 후처리 및 의도화 흐름

### 7.1 클러스터 특징어 추출 방식

#### TF-IDF 기반 키워드 추출
- 클러스터 내 모든 포스트의 제목 + 본문을 하나의 문서로 간주
- TF-IDF 점수 계산
- 상위 10개 키워드 추출

#### 추가 특징어
- 서브레딧 이름 (subreddit)
- 자주 등장하는 동사/명사 조합
- 월별 트렌드 키워드 (GSC 연계)

### 7.2 LLM 입력 구성 규칙

#### 입력 구성 요소
1. **대표 샘플**: 클러스터의 대표 포스트 1개 (제목 + 본문)
2. **키워드**: TF-IDF로 추출한 상위 10개 키워드
3. **월별 트렌드 요약**: Reddit 월별 집계 데이터 요약
4. **GSC 데이터**: 관련 키워드의 Impressions, Clicks, CTR 요약
5. **SERP AIO**: 해당 키워드의 AI Overview 요약 (있는 경우)

#### 입력 프롬프트 구조
```
You are analyzing a cluster of Reddit posts about kitchen lifestyle topics.

Representative Post:
[대표 샘플 제목 + 본문]

Key Keywords: [키워드 리스트]

Monthly Trends (Reddit):
[월별 포스트 수, 업보트 수 요약]

Search Console Data:
[관련 쿼리의 Impressions, Clicks 요약]

SERP AI Overview:
[AI Overview 텍스트, 있는 경우]

Please analyze this cluster and provide the following information...
```

### 7.3 LLM 산출물 정의

#### 필수 출력 필드

**category** (string)
- 4개 대주제 중 하나: "Spring Recipes", "Spring Kitchen Styling", "Refrigerator Organization", "Vegetable Prep & Handling"

**topic_title** (string)
- 클러스터를 대표하는 주제 제목 (한국어)
- 예: "봄 제철 야채를 활용한 가벼운 레시피"

**primary_question** (string)
- 이 주제에서 가장 핵심적인 질문 (한국어)
- 예: "봄 제철 야채로 어떤 가벼운 레시피를 만들 수 있을까?"

**related_questions** (array of strings)
- 관련 질문 3-5개 (한국어)
- 예: ["봄 야채 보관법은?", "봄 레시피 준비 시간은 얼마나 걸리나요?"]

**blog_angle** (string)
- 블로그 콘텐츠 각도 (한국어)
- 예: "봄 제철 야채 5가지와 각각 활용 가능한 레시피 소개"

**social_angle** (string)
- 소셜 미디어 콘텐츠 각도 (한국어)
- 예: "봄 야채로 만든 3가지 레시피를 한 번에 보여주는 리els"

**why_now** (string)
- 왜 지금 이 주제인가 (한국어)
- 계절성, 트렌드, 검색량 등을 근거로 설명

**evidence_summary** (string)
- Evidence Pack 요약 (한국어)
- Reddit 반응, GSC 검색량, SERP AIO 존재 여부 등을 요약

#### JSON 스키마 강제
- LLM 출력은 반드시 JSON 형식
- JSON 스키마 검증 후 저장
- 파싱 실패 시 재시도 또는 수동 검토

---

## 8. 시계열 분석 및 트렌드 판단 기준

### 8.1 월 단위 집계 방식

#### Reddit 데이터
- 포스트의 `created_utc`를 기준으로 YYYY-MM 형식으로 그룹화
- 월별 집계 지표:
  - 포스트 수
  - 평균 업보트
  - 평균 댓글 수
  - 총 업보트
  - 총 댓글 수

#### GSC 데이터
- Date를 기준으로 YYYY-MM 형식으로 그룹화
- Query별 월별 집계:
  - 총 Impressions
  - 총 Clicks
  - 평균 CTR
  - 평균 Position

### 8.2 Reddit/GSC 신호 결합 방식

#### 신호 정규화
- Reddit 신호: 월별 포스트 수 + 평균 업보트 (0-1 스케일 정규화)
- GSC 신호: 월별 Impressions (0-1 스케일 정규화)

#### 결합 점수
- 가중 평균: Reddit 0.6 + GSC 0.4
- 또는 곱셈 방식: Reddit 신호 × GSC 신호

#### 트렌드 방향 판단
- 전월 대비 증감률 계산
- 3개월 이동 평균으로 추세 파악
- 계절성 패턴 식별 (봄 시즌 집중도)

### 8.3 SERP AIO를 포화도 참고 지표로 활용하는 방법

#### 포화도 판단
- AI Overview가 존재하는 키워드 → 높은 포화도
- AI Overview가 없는 키워드 → 낮은 포화도 또는 니치

#### 활용 방식
- Emerging: AI Overview 없음 + Reddit/GSC 신호 상승
- Competitive: AI Overview 있음 + Reddit/GSC 신호 높음
- Saturated: AI Overview 있음 + Reddit/GSC 신호 하락
- Niche: AI Overview 없음 + Reddit/GSC 신호 낮음

### 8.4 Emerging / Competitive / Saturated / Niche 상태 정의

#### Emerging (신흥)
- AI Overview: 없음
- Reddit 신호: 최근 3개월 상승 추세
- GSC 신호: 최근 3개월 상승 추세
- 판단: 새로운 트렌드, 기회 가능성 높음

#### Competitive (경쟁)
- AI Overview: 있음
- Reddit 신호: 높음 (상위 25%)
- GSC 신호: 높음 (상위 25%)
- 판단: 이미 경쟁이 치열하지만, 여전히 기회 존재

#### Saturated (포화)
- AI Overview: 있음
- Reddit 신호: 하락 추세 또는 정체
- GSC 신호: 하락 추세 또는 정체
- 판단: 시장이 포화 상태, 차별화 전략 필요

#### Niche (니치)
- AI Overview: 없음
- Reddit 신호: 낮음 (하위 25%)
- GSC 신호: 낮음 (하위 25%)
- 판단: 작은 시장이지만 경쟁이 적어 기회 가능

---

## 9. LLM 호출 정책 및 비용 통제

### 9.1 클러스터 단위 호출 원칙

- 문서 단위가 아닌 클러스터 단위로만 LLM 호출
- 하나의 클러스터당 1회 호출
- 대표 샘플 + 특징어 + 트렌드 요약을 입력으로 사용

### 9.2 상위 클러스터만 Q&A brief 생성

#### 우선순위 기준
1. 클러스터 크기 (큰 클러스터 우선)
2. 평균 업보트 (높은 반응 우선)
3. GSC 연관성 (검색량 높은 키워드 포함)

#### 상위 N개만 선택
- 상위 50개 클러스터만 LLM 호출
- 나머지는 메타데이터만 저장

### 9.3 JSON 스키마 강제 및 검증

#### 스키마 정의
- JSON Schema를 명시적으로 정의
- LLM 프롬프트에 스키마 포함
- 출력 형식 강제 (JSON mode 사용)

#### 검증 규칙
- 필수 필드 존재 여부 확인
- 데이터 타입 검증
- 문자열 길이 제한
- 파싱 실패 시 재시도 (최대 3회)

### 9.4 결과 캐시 및 재실행 전략

#### 캐시 전략
- 동일 클러스터 ID에 대한 LLM 결과는 캐시
- 클러스터가 변경되지 않으면 재호출하지 않음
- 캐시 키: 클러스터 ID + 클러스터 해시

#### 재실행 전략
- 데이터 업데이트 시에만 재실행
- 부분 업데이트: 변경된 클러스터만 재호출
- 전체 재실행: 주기적으로 (예: 월 1회)

#### 비용 모니터링
- LLM 호출 횟수 로깅
- 토큰 사용량 추적
- 비용 상한 설정 및 알림

---

## 10. 대시보드 화면 구성

### 10.1 Raw 데이터 검증 화면

#### 기능
- Reddit 포스트 목록 표시 (필터링 가능)
- GSC 데이터 표시 (Query별 Impressions, Clicks)
- SERP AIO 데이터 표시
- 데이터 품질 지표 (중복률, 노이즈 비율 등)

#### 필터링 옵션
- 키워드별 필터
- 날짜 범위 필터
- 서브레딧 필터
- 업보트/댓글 수 기준 필터

### 10.2 클러스터 + 시계열 분석 화면

#### 클러스터 시각화
- 클러스터 목록 (카테고리별 그룹화)
- 클러스터 크기, 평균 업보트 표시
- 대표 샘플 미리보기
- 클러스터별 특징어 표시

#### 시계열 차트
- 월별 포스트 수 추이
- 월별 평균 업보트 추이
- GSC Impressions 추이
- 트렌드 상태 표시 (Emerging/Competitive/Saturated/Niche)

#### 인터랙션
- 클러스터 클릭 시 상세 정보 표시
- 월별 데이터 드릴다운
- 클러스터별 포스트 목록 보기

### 10.3 콘텐츠 주제 발굴 화면

#### 주제 카드 표시
- 카테고리별 탭 (4개 대주제)
- 각 주제 카드:
  - topic_title
  - primary_question
  - related_questions
  - blog_angle
  - social_angle
  - why_now
  - evidence_summary

#### 필터링 및 정렬
- 카테고리별 필터
- 트렌드 상태별 필터 (Emerging/Competitive 등)
- 우선순위 정렬 (클러스터 크기, 반응 등)

#### Evidence Pack 표시
- Reddit 포스트 샘플 (대표 샘플 + 관련 포스트)
- GSC 검색량 데이터
- SERP AIO 존재 여부
- 월별 트렌드 차트

#### 내보내기
- 주제 리스트 CSV 다운로드
- Evidence Pack PDF 생성 (선택사항)

---

## 11. PoC 성공 기준

### 11.1 정량 기준

#### 데이터 수집
- Reddit: 키워드별 최소 500개 이상 포스트 수집
- GSC: 1년치 데이터 정상 업로드 및 파싱
- SERP AIO: 주요 키워드 10개 이상 수집

#### 클러스터링
- 총 클러스터 수: 50개 이상
- Noise 비율: 30% 이하
- 평균 클러스터 크기: 5개 이상

#### LLM 결과
- Q&A brief 생성: 50개 이상
- JSON 파싱 성공률: 95% 이상
- 카테고리 매핑 정확도: 90% 이상

### 11.2 정성 기준

#### 기획 활용 가능성
- 주제 제목이 명확하고 구체적
- primary_question이 실제 사용자 질문과 유사
- blog_angle과 social_angle이 실행 가능
- why_now가 설득력 있음
- Evidence Pack이 충분한 근거 제공

#### 데이터 품질
- Reddit 포스트가 질문형/How-to/아이디어성 콘텐츠 중심
- 중복 제거가 효과적
- 클러스터가 의미 있게 형성됨
- 시계열 트렌드가 계절성 반영

### 11.3 운영 기준

#### 재실행 안정성
- 전체 파이프라인 재실행 시 오류 없음
- 데이터 업데이트 시 증분 처리 정상 작동
- LLM 호출 실패 시 재시도 메커니즘 작동

#### 배포 상태
- Railway에서 Streamlit 서비스 정상 배포
- Worker 파이프라인 정상 실행
- PostgreSQL 연결 안정
- 대시보드 로딩 시간 3초 이하

#### 모니터링
- 로그 수집 정상
- 에러 추적 가능
- 비용 모니터링 가능

---

## 부록: 용어 정의

- **Evidence Pack**: Reddit 포스트, GSC 데이터, SERP AIO를 포함한 주제 발굴 근거 패키지
- **대표 샘플**: 클러스터 내 centroid와 가장 유사한 포스트
- **특징어**: TF-IDF로 추출한 클러스터 대표 키워드
- **트렌드 상태**: Emerging/Competitive/Saturated/Niche 중 하나
- **월 단위 집계**: YYYY-MM 형식으로 그룹화한 시계열 데이터

---

**문서 버전**: 1.0  
**최종 수정일**: 2025-01-08  
**작성자**: Kitchen Seasonal Content POC Team
