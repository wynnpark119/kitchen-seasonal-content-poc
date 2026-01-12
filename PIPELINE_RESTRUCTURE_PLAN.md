# 파이프라인 재구성 계획

## [1] 현재 상태 파악

### Reddit Raw 데이터 테이블

**테이블**: `raw_reddit_posts` (`migrations/001_initial_schema.sql:34-50`)

**필드**:
- `reddit_post_id` (VARCHAR(50), PK)
- `subreddit` (VARCHAR(100))
- `title` (TEXT, NOT NULL)
- `body` (TEXT)
- `author` (VARCHAR(100))
- `created_utc` (BIGINT)
- `upvotes` (INTEGER, 기본값 0)
- `num_comments` (INTEGER, 기본값 0)
- `permalink` (TEXT)
- `url` (TEXT)
- `keyword` (VARCHAR(200), NOT NULL)
- `raw_json` (JSONB)
- `created_at`, `updated_at` (TIMESTAMP)

**댓글 테이블**: `raw_reddit_comments` (`migrations/001_initial_schema.sql:58-76`)
- `reddit_comment_id` (VARCHAR(50), PK)
- `reddit_post_id` (VARCHAR(50), FK)
- `body` (TEXT)
- `upvotes` (INTEGER)
- `is_top` (BOOLEAN)

### 기존 4개 카테고리

**위치**: `worker/pipeline/config.py:57-62`

```python
CATEGORIES = [
    "SPRING_RECIPES",
    "SPRING_KITCHEN_STYLING",
    "REFRIGERATOR_ORGANIZATION",
    "VEGETABLE_PREP_HANDLING"
]
```

### 기존 Embedding 관련 코드 (비활성화 대상)

**비활성화 대상 파일/함수**:

1. **`worker/pipeline/embedding.py`** - 전체 파일
   - `generate_embeddings()` - Post 단위 임베딩 생성 (비활성화)
   - `generate_embeddings_batch()` - 배치 임베딩 (비활성화)
   - `truncate_text_to_max_tokens()` - 유지 (클러스터 요약용)

2. **`worker/pipeline/clustering.py`** - 수정 필요
   - `load_embeddings()` - 임베딩 로드 (비활성화)
   - `run_clustering()` - HDBSCAN 클러스터링 (비활성화)
   - 새로운 TF-IDF 기반 클러스터링으로 교체

3. **`worker/run_pipeline.py`** - 수정 필요
   - `run_analyze_mode()` 내 `generate_embeddings()` 호출 제거
   - 새로운 클러스터링 모드 추가

4. **`scripts/retry_failed_embeddings.py`** - 비활성화
   - Post 단위 재처리 스크립트 (더 이상 사용 안 함)

### 기존 SERP 수집 코드

**파일**: `worker/pipeline/collect_serp_aio.py`
- 현재: AI Overview만 수집
- 변경: 일반 검색 결과도 수집하도록 확장 필요

## [2] 새로운 파이프라인 구조

### 단계 1: TF-IDF 기반 4개 클러스터링

**입력**: `raw_reddit_posts` 테이블의 모든 포스트
**출력**: 4개 클러스터 (각 카테고리 1개씩)

**구현 파일**: `worker/pipeline/tfidf_clustering.py` (신규)

**알고리즘**:
1. Reddit 포스트 텍스트 전처리 (title + body)
2. TF-IDF 벡터화
3. 키워드 기반 카테고리 매칭 (기존 4개 카테고리)
4. 각 카테고리별로 포스트 할당

**출력**:
- `cluster_id` (1~4)
- `category` (SPRING_RECIPES 등)
- 대표 post 10개 (upvotes + num_comments 기준)
- 대표 키워드 Top 20 (TF-IDF 기반)
- 클러스터 요약 텍스트 (3~5줄)

**저장 위치**: `clusters` 테이블 (기존 스키마 활용)

### 단계 2: 클러스터별 SERP 질문 생성

**입력**: 각 클러스터의 대표 키워드 및 요약
**출력**: 클러스터별 50개 검색 질문

**구현 파일**: `worker/pipeline/generate_serp_queries.py` (신규)

**질문 생성 전략**:
- 정보 탐색: "why do people struggle with X", "how to solve Y"
- 문제 인식: "common problems with X", "X challenges"
- 비교: "X vs Y pros cons", "best X for Y"
- 사례: "real world examples of X", "X success stories"
- 트렌드: "X trends 2025", "future of X"

**저장 위치**: `cluster_serp_queries` 테이블 (신규)

### 단계 3: SERP API 수집/적재

**입력**: 클러스터별 50개 질문
**출력**: 검색 결과 (URL, title, snippet 등)

**구현 파일**: `worker/pipeline/collect_serp_results.py` (신규)

**필수 필드**:
- `cluster_id`
- `query`
- `url`
- `title`
- `snippet`
- `source` (도메인)
- `fetched_at`

**저장 위치**: `serp_results` 테이블 (신규)

**재시도 정책**:
- 네트워크 타임아웃: 30초
- 재시도: 최대 3회, exponential backoff
- Rate limiting: 1초 간격

### 단계 4: 클러스터 요약 임베딩

**입력**: 클러스터 요약 텍스트만
**출력**: 클러스터 임베딩 벡터

**구현 파일**: `worker/pipeline/cluster_embedding.py` (신규)

**임베딩 대상**:
- 클러스터 요약 (3~5줄)
- 대표 키워드 (Top 20)
- 대표 SERP snippet 일부 (선택적)

**저장 위치**: `cluster_embeddings` 테이블 (신규)

## [3] 데이터베이스 스키마 변경

### 신규 테이블

1. **`cluster_serp_queries`**
```sql
CREATE TABLE cluster_serp_queries (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    query_type VARCHAR(50), -- 'info_search', 'problem', 'comparison', 'case_study', 'trend'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cluster_serp_queries_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT uk_cluster_query UNIQUE (cluster_id, query)
);
```

2. **`serp_results`**
```sql
CREATE TABLE serp_results (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    source VARCHAR(255), -- 도메인
    position INTEGER, -- 검색 결과 순위
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_serp_results_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT uk_serp_result_url_query UNIQUE (url, query)
);
CREATE INDEX idx_serp_results_cluster_id ON serp_results(cluster_id);
CREATE INDEX idx_serp_results_query ON serp_results(query);
CREATE INDEX idx_serp_results_source ON serp_results(source);
```

3. **`cluster_embeddings`**
```sql
CREATE TABLE cluster_embeddings (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    embedding_json JSONB NOT NULL,
    model_name VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-large',
    dim INTEGER NOT NULL DEFAULT 3072,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_cluster_embedding_run UNIQUE (cluster_id, created_from_run_id),
    CONSTRAINT fk_cluster_embeddings_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT fk_cluster_embeddings_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);
```

## [4] 실행 순서

1. **클러스터링**: `python worker/run_pipeline.py --mode=cluster_tfidf`
2. **질문 생성**: `python worker/run_pipeline.py --mode=generate_queries`
3. **SERP 수집**: `python worker/run_pipeline.py --mode=collect_serp`
4. **클러스터 임베딩**: `python worker/run_pipeline.py --mode=embed_clusters`

또는 전체 실행: `python worker/run_pipeline.py --mode=cluster_pipeline`
