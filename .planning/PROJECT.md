# Olist E-Commerce Marketing Dashboard

## What This Is

Olist 브라질 이커머스 데이터셋(10만건 주문, 2016-2018)을 활용한 마케터용 종합 대시보드. 고객 획득부터 구매, 배송, 리뷰까지 전체 고객 저니를 시각화하고 분석할 수 있는 Streamlit 기반 대시보드.

## Core Value

마케터가 전체 고객 저니 데이터를 한 곳에서 탐색하고, 인사이트를 빠르게 발견할 수 있어야 한다.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 퍼널 분석 (주문→결제→배송→리뷰 전환율 및 이탈 지점)
- [ ] 고객 세그먼테이션 (RFM 분석, 재구매율, 고객 생애 가치)
- [ ] 상품/카테고리별 성과 분석 (매출, 리뷰 점수, 판매량)
- [ ] 지역별 분석 (배송 시간, 매출 분포, 지도 시각화)
- [ ] 시계열 트렌드 (월별/주별 매출, 주문량 추이)
- [ ] 결제 분석 (결제 수단별, 할부 패턴)
- [ ] 리뷰/만족도 분석 (점수 분포, 배송 시간과 리뷰 상관관계)
- [ ] 셀러 성과 분석 (셀러별 매출, 배송 성과, 리뷰 점수)
- [ ] 코호트 분석 (월별 코호트 리텐션)
- [ ] 배송 성과 분석 (예상 vs 실제 배송일, 지연율)

### Out of Scope

- 실시간 데이터 연동 — 정적 Kaggle 데이터셋 사용 (2016-2018)
- 사용자 인증/로그인 — 단일 사용자 대시보드
- 데이터 편집/입력 — 읽기 전용 분석 대시보드
- 모바일 최적화 — 데스크톱 중심 대시보드

## Context

- **데이터소스**: Kaggle Olist Brazilian E-Commerce Dataset (9개 CSV 테이블)
  - orders, customers, order_items, payments, reviews, products, sellers, geolocation, category_translation
- **데이터 규모**: ~100K 주문, 2016-2018
- **기존 프로젝트**: kitchen-seasonal-content-poc (Streamlit + Python 기반 프로젝트가 이미 존재)
- **타겟 사용자**: 마케터 (전체 고객 저니 분석)

## Constraints

- **Tech Stack**: Streamlit + Pandas + Plotly — 가장 쉽고 직관적인 조합
- **Data Storage**: CSV 파일 직접 로드 (DB 없음) — 설정 최소화
- **Language**: Python — 기존 프로젝트와 일관성
- **Data**: Kaggle Olist 데이터셋 고정 — 실시간 연동 없음

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Streamlit 사용 | 기존 프로젝트에서 사용 중, Python 기반 빠른 개발 | — Pending |
| CSV/Pandas 직접 로드 | DB 설정 없이 가장 단순한 방식 | — Pending |
| Plotly 시각화 | 인터랙티브 차트, Streamlit과 호환성 좋음 | — Pending |
| 전체 저니 분석 포함 | 마케터가 원하는 모든 지표를 한 대시보드에 | — Pending |

---
*Last updated: 2026-02-18 after initialization*
