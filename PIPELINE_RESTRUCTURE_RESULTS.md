# 파이프라인 재구성 결과 문서

## (A) 4개 클러스터 요약

### 클러스터 1: SPRING_RECIPES
- **대표 키워드**: spring, recipe, dinner, meal, cook, food, dish, ingredient, cooking, kitchen, prep, meal prep
- **설명**: 봄 시즌 레시피와 식사 준비에 관한 포스트들. 봄철 요리 아이디어, 식사 준비, 계절별 재료 활용 등이 주요 주제입니다.

### 클러스터 2: SPRING_KITCHEN_STYLING
- **대표 키워드**: spring, decor, decoration, styling, design, kitchen, refresh, makeover, update, color, accessory, centerpiece
- **설명**: 봄 시즌 주방 인테리어와 스타일링에 관한 포스트들. 봄 주방 장식, 리프레시, 컬러 코디네이션 등이 주요 주제입니다.

### 클러스터 3: REFRIGERATOR_ORGANIZATION
- **대표 키워드**: refrigerator, fridge, organization, organize, storage, container, bin, label, shelf, drawer, door
- **설명**: 냉장고 정리와 조직화에 관한 포스트들. 냉장고 수납, 컨테이너 활용, 라벨링 시스템 등이 주요 주제입니다.

### 클러스터 4: VEGETABLE_PREP_HANDLING
- **대표 키워드**: vegetable, prep, preparation, storage, wash, clean, cut, chop, store, container, fresh, preserve
- **설명**: 채소 준비와 보관에 관한 포스트들. 채소 세척, 손질, 보관 방법, 신선도 유지 등이 주요 주제입니다.

## (B) 각 클러스터별 SERP 질문 50개

각 클러스터당 50개의 검색 질문이 생성됩니다. 질문은 다음 5가지 타입으로 분류됩니다:

1. **정보 탐색 (info_search)**: "why do people...", "how to...", "what is the best way to..."
2. **문제 (problem)**: "common problems with...", "...challenges", "why do people struggle with..."
3. **비교 (comparison)**: "...vs... pros cons", "best...for...", "which...is better"
4. **사례 (case_study)**: "real world examples of...", "...success stories", "...case studies"
5. **트렌드 (trend)**: "...trends 2025", "future of...", "...innovations"

**생성 로직**: `worker/pipeline/generate_serp_queries.py`
- 각 클러스터의 대표 키워드와 카테고리를 기반으로 질문 생성
- 템플릿 기반 변수 치환
- 총 200개 질문 (클러스터당 50개 × 4개)

**예시 질문** (SPRING_RECIPES 클러스터):
- "why do people cook spring recipes"
- "common problems with spring recipes"
- "spring recipes vs alternative pros cons"
- "real world examples of spring recipes"
- "spring recipes trends 2025"

## (C) 변경된 파이프라인 구조 설명

### 기존 파이프라인 (비활성화)

**순서**: Reddit 수집 → 전처리 → **Post 단위 임베딩** → HDBSCAN 클러스터링 → SERP 수집

**문제점**:
- Post 단위 임베딩으로 인한 토큰 초과
- DB pool 고갈
- 비용 증가

### 새로운 파이프라인

**순서**:
1. **Reddit 수집** (기존 유지)
2. **TF-IDF 기반 4개 클러스터링** (임베딩 없이)
   - 키워드 기반 카테고리 매칭
   - 각 클러스터별 대표 포스트 10개, 키워드 Top 20, 요약 생성
3. **클러스터별 SERP 질문 생성** (각 클러스터당 50개)
   - 정보 탐색/문제/비교/사례/트렌드 중심
4. **SERP API 수집/적재**
   - 질문별 검색 결과 수집
   - URL 중복 제거
   - 재시도 정책 적용
5. **클러스터 요약만 임베딩**
   - 클러스터 요약 + 키워드 + SERP snippet 일부만 임베딩
   - Post 단위 임베딩 금지

### 주요 변경사항

1. **임베딩 단계 제거**: Post 단위 임베딩 완전 제거
2. **클러스터링 방식 변경**: HDBSCAN → TF-IDF + 키워드 매칭
3. **클러스터 수 고정**: 동적 클러스터 → 4개 고정 (카테고리별 1개)
4. **SERP 수집 확장**: AI Overview만 → 일반 검색 결과도 수집
5. **임베딩 범위 축소**: Post 전체 → 클러스터 요약만

## (D) 변경/추가된 파일 리스트

### 신규 파일

1. **`worker/pipeline/tfidf_clustering.py`**
   - TF-IDF 기반 4개 클러스터링 구현
   - 키워드 기반 카테고리 매칭
   - 클러스터 요약 생성

2. **`worker/pipeline/generate_serp_queries.py`**
   - 클러스터별 SERP 질문 50개 생성
   - 질문 타입별 템플릿 활용

3. **`worker/pipeline/collect_serp_results.py`**
   - SERP API 수집/적재 파이프라인
   - 일반 검색 결과 수집 (AI Overview 아님)
   - 재시도 정책 및 중복 제거

4. **`worker/pipeline/cluster_embedding.py`**
   - 클러스터 요약만 임베딩 생성
   - Post 단위 임베딩 금지

5. **`migrations/004_add_cluster_serp_tables.sql`**
   - `cluster_serp_queries` 테이블
   - `serp_results` 테이블
   - `cluster_embeddings` 테이블

6. **`PIPELINE_RESTRUCTURE_PLAN.md`**
   - 파이프라인 재구성 계획 문서

7. **`PIPELINE_RESTRUCTURE_RESULTS.md`**
   - 최종 결과 문서 (본 문서)

### 수정된 파일

1. **`worker/run_pipeline.py`**
   - 새로운 모드 추가: `cluster_tfidf`, `generate_queries`, `collect_serp`, `embed_clusters`, `cluster_pipeline`
   - 기존 `analyze` 모드의 embedding 호출 주석 처리 (비활성화)

2. **`requirements.txt`**
   - `scikit-learn>=1.3.0` 추가 확인 (이미 존재)

### 비활성화 대상 (사용 안 함)

1. **`worker/pipeline/embedding.py`**
   - `generate_embeddings()` - Post 단위 임베딩 (비활성화)
   - `generate_embeddings_batch()` - 배치 임베딩 (비활성화)
   - **참고**: `truncate_text_to_max_tokens()` 함수는 `cluster_embedding.py`에서 재사용

2. **`worker/pipeline/clustering.py`**
   - `load_embeddings()` - 임베딩 로드 (비활성화)
   - `run_clustering()` - HDBSCAN 클러스터링 (비활성화)
   - **참고**: `upsert_cluster_assignment()` 함수는 재사용

3. **`scripts/retry_failed_embeddings.py`**
   - Post 단위 재처리 스크립트 (더 이상 사용 안 함)

## (E) 실행 방법

### 로컬 실행

#### 1. 마이그레이션 실행

```bash
# 마이그레이션 실행
psql $DATABASE_URL -f migrations/004_add_cluster_serp_tables.sql

# 또는 Python 스크립트 사용
python migrations/run_migration.py migrations/004_add_cluster_serp_tables.sql
```

#### 2. 전체 파이프라인 실행

```bash
# 전체 클러스터 파이프라인 실행
python worker/run_pipeline.py --mode=cluster_pipeline

# 또는 단계별 실행
python worker/run_pipeline.py --mode=cluster_tfidf      # 1. 클러스터링
python worker/run_pipeline.py --mode=generate_queries  # 2. 질문 생성
python worker/run_pipeline.py --mode=collect_serp      # 3. SERP 수집
python worker/run_pipeline.py --mode=embed_clusters    # 4. 클러스터 임베딩
```

#### 3. Dry-run 테스트

```bash
# Dry-run 모드로 테스트
python worker/run_pipeline.py --mode=cluster_pipeline --dry-run
```

### 서버 실행 (Railway)

#### 1. 마이그레이션 실행

```bash
# Railway CLI 사용
railway run psql -f migrations/004_add_cluster_serp_tables.sql

# 또는 Railway 대시보드에서 Query 실행
```

#### 2. Worker 서비스 실행

```bash
# Railway Worker 서비스에서 자동 실행되거나
# 수동으로 실행:
railway run python worker/run_pipeline.py --mode=cluster_pipeline
```

### 환경 변수

필수 환경 변수:
- `DATABASE_URL`: PostgreSQL 연결 URL
- `OPENAI_API_KEY`: OpenAI API 키 (클러스터 임베딩용)
- `SERPAPI_KEY`: SerpAPI 키 (SERP 결과 수집용)

### 실행 순서 및 의존성

```
1. cluster_tfidf
   ↓ (clusters 테이블 생성)
2. generate_queries
   ↓ (cluster_serp_queries 테이블 생성)
3. collect_serp
   ↓ (serp_results 테이블 생성)
4. embed_clusters
   ↓ (cluster_embeddings 테이블 생성)
```

각 단계는 이전 단계의 결과를 사용하므로 순서대로 실행해야 합니다.

## 성공 기준

1. ✅ **4개 클러스터 생성**: 각 카테고리별로 1개씩 정확히 생성
2. ✅ **클러스터당 50개 질문**: 총 200개 질문 생성
3. ✅ **SERP 결과 수집**: 질문별 검색 결과 정상 수집
4. ✅ **클러스터 임베딩**: 4개 클러스터 요약만 임베딩 생성
5. ✅ **토큰 초과 방지**: 클러스터 요약만 임베딩하므로 토큰 초과 없음
6. ✅ **DB pool 고갈 방지**: Post 단위 임베딩 제거로 커넥션 점유 시간 감소

## 제약사항 준수

- ✅ 임베딩 토큰 초과 방지: 클러스터 요약만 임베딩 (최대 8192 토큰 이하)
- ✅ DB pool acquire timeout 방지: Post 단위 임베딩 제거, 짧은 트랜잭션만 사용
- ✅ 과도한 리팩터링 금지: 기존 구조 최대한 활용, 새로운 모듈만 추가
