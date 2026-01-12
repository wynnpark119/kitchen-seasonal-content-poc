# Streamlit 대시보드 구현 완료

## 목표
DB에 저장된 분석 결과를 조회하여 콘텐츠 기획에 활용하는 대시보드

---

## 구현된 파일

### 1. `web/app.py`
- Streamlit 메인 앱
- 6개 탭 구성
- 읽기 전용 (SELECT only)
- 데이터 없을 경우 에러 처리

### 2. `web/db_queries.py`
- DB 조회 헬퍼 함수
- LG 도메인 체크 함수
- Cited sources 파싱 함수

---

## 탭 구성

### TAB 0: Executive Overview
- 전체 Master Topic 수
- 시즌성 vs 비시즌성 Topic 비율
- AIO AVAILABLE vs NOT_AVAILABLE 비율
- LG 도메인 인용된 Topic 수 / 비율
- 최근 3개월 기준 우선 검토 Master Topic Top 5

### TAB 1: Raw Data Explorer
- Reddit Posts: keyword, title, upvotes, num_comments, permalink
- SERP AI Overview: query, aio_status, aio_text, cited_sources
- 필터/정렬/CSV 다운로드 지원

### TAB 2: Cluster & Trend Explorer
- 클러스터 리스트 및 상세
- 월 단위 시계열 차트
- 대표 포스트 목록
- 시즌성/비시즌성 해석 표시

### TAB 3: Master Topic Explorer (핵심)
- Master Topic 카드 리스트
- 필터: Category, AIO Status, LG Citation
- 상세: Primary Question, Related Questions, Why Now, Blog Angle, Social Angle, Evidence Pack
- CSV Export

### TAB 4: SERP AI Overview Audit (LG 핵심 Audit)
- AIO Query 테이블
- AIO 상세 (텍스트, 인용 URL 리스트)
- 도메인 점유 분석
- LG 도메인 인용 여부 체크
- 해석 배지: 최우선 개선 기회 / 선점 기회 / 방어/확장

### TAB 5: Opportunity Matrix
- 2D Scatter Plot: Reddit Engagement vs AIO Presence
- 색상: LG Citation 여부
- 사분면 해석: 선점 / SEO/AIO 대응 최우선 / 후순위 / 보류

---

## 실행 방법

### 로컬 실행

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 환경 변수 설정
export DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway"

# Streamlit 실행
streamlit run web/app.py
```

### Railway 배포

Railway에서 자동 배포되도록 설정되어 있습니다.

---

## 주요 기능

### 1. LG 도메인 체크
- `lge.com`, `lg.com`, `lgstory.com`, `lg.co.kr` 체크
- Cited sources에서 자동 감지

### 2. 데이터 없을 경우 처리
- 모든 쿼리에 try-except 적용
- "No data available" 명확 표시
- 앱이 깨지지 않음

### 3. 필터/정렬/검색
- Reddit Posts: keyword 필터, upvotes 정렬
- Master Topics: Category, AIO Status, LG Citation 필터

### 4. CSV 다운로드
- Reddit Posts
- SERP AIO
- Master Topics (개별)
- Opportunity Matrix

---

## 완료 조건

### ✅ 구현 완료
- [x] 6개 탭 모두 구현
- [x] DB 조회 함수 구현
- [x] LG 도메인 체크 로직
- [x] 데이터 없을 경우 에러 처리
- [x] 필터/정렬/CSV 다운로드
- [x] 시각화 (Plotly 차트)

### ⚠️ 주의사항
- 데이터가 없을 경우에도 앱이 정상 작동
- 모든 쿼리는 읽기 전용 (SELECT only)
- LG 도메인 체크는 cited_sources_json 파싱 기반

---

## 다음 단계

1. 실제 데이터로 테스트
2. 성능 최적화 (필요 시)
3. 추가 필터/정렬 옵션 (필요 시)
