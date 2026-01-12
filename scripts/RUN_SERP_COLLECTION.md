# SERP 수집 스크립트 실행 가이드

## 개요

4개 topic_category별 SERP 쿼리 리스트로 SERP API 요청을 보내고, 결과를 DB에 topic_category 기준으로 구분 저장하는 스크립트입니다.

## 사전 준비

### 1. 환경변수 설정

필수 환경변수:
- `SERP_API_KEY`: SerpAPI 키 (필수)

선택적 환경변수:
- `SERP_ENGINE`: 검색 엔진 (기본: `google`)
- `SERP_LOCATION`: 위치 (기본: `us`)
- `SERP_GL`: 국가 코드 (기본: `us`)
- `SERP_HL`: 언어 코드 (기본: `en`)
- `SERP_NUM_RESULTS`: 쿼리당 결과 수 (기본: `10`)
- `SERP_TIMEOUT_SEC`: 타임아웃 (기본: `30`)
- `SERP_CONCURRENCY`: 동시성 (기본: `2`)

### 2. 데이터베이스 연결

`DATABASE_URL` 환경변수가 설정되어 있어야 합니다.

## 실행 방법

```bash
# 환경변수 설정 후 실행
export SERP_API_KEY="your-api-key"
export DATABASE_URL="postgresql://..."

# 스크립트 실행
python3 scripts/run_serp_collection.py
```

또는 `.env` 파일 사용:

```bash
# .env 파일에 환경변수 설정
SERP_API_KEY=your-api-key
DATABASE_URL=postgresql://...

# 스크립트 실행 (dotenv 자동 로드)
python3 scripts/run_serp_collection.py
```

## 수집되는 쿼리

각 topic_category별로 25개씩 총 100개의 쿼리가 실행됩니다:

- **SPRING_RECIPES**: 25개 쿼리
- **REFRIGERATOR_ORGANIZATION**: 25개 쿼리
- **VEGETABLE_PREP_HANDLING**: 25개 쿼리
- **SPRING_KITCHEN_STYLING**: 25개 쿼리

## 출력 형식

스크립트 실행 후 다음 정보가 출력됩니다:

### A) 전체 통계
- 총 topic_category 수
- 총 query 수
- 총 SERP row 저장 수
- 중복으로 스킵된 row 수
- 실패 query 수 (에러 요약 Top 5)

### B) topic_category별 통계 테이블
- topic_category
- queries_run
- results_saved
- unique_urls
- last_fetched_at

### C) 샘플 출력
각 topic_category별로 5개 row를 출력:
- query
- title
- url
- snippet (100~200자)

### D) 최종 판정
- DB 적재: SUCCESS / FAIL
- 주제 구분 저장: PASS / FAIL
- 다음 단계 진행 가능: YES / NO

## 데이터베이스 스키마

결과는 `serp_results` 테이블에 저장됩니다:

- `id`: Primary key
- `topic_category`: 주제 카테고리 (필수)
- `query`: 검색 쿼리 (필수)
- `url`: 결과 URL (필수)
- `title`: 결과 제목
- `snippet`: 결과 스니펫
- `position`: 검색 결과 순위
- `source`: 도메인
- `engine`: 검색 엔진 (기본: google)
- `dedup_hash`: 중복 방지 해시
- `fetched_at`: 수집 시간
- `created_at`: 생성 시간

UNIQUE 제약조건: `(topic_category, query, url)`

## 주의사항

1. **API 비용**: 각 쿼리마다 SerpAPI 비용이 발생합니다 (100개 쿼리 = 100회 API 호출)
2. **Rate Limiting**: 동시성 제어로 API 호출 속도가 제한됩니다
3. **재시도**: 429/5xx/timeout 에러만 최대 3회 재시도합니다
4. **중복 방지**: 동일한 `(topic_category, query, url)` 조합은 스킵됩니다

## 마이그레이션

스크립트 실행 시 자동으로 마이그레이션이 실행됩니다:
- `topic_category` 컬럼 추가
- `engine` 컬럼 추가
- `dedup_hash` 컬럼 추가
- 관련 인덱스 추가
- UNIQUE 제약조건 업데이트

수동 실행이 필요한 경우:

```bash
python3 migrations/run_migration.py migrations/005_add_topic_category_to_serp_results.sql
```
