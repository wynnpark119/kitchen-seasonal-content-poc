# Topic-Centric Dashboard 구현 계획

## (A) 현재 상태 진단

### 현재 대시보드가 원본만 보여주는 이유

**근거 (파일/라인 기준):**

1. **`web/db_queries.py:164-202`** - `get_reddit_posts()` 함수
   - `raw_reddit_posts` 테이블을 직접 조회
   - 키워드 필터링만 지원, topic/cluster 기반 필터링 없음
   - 반환 컬럼: `keyword, title, upvotes, num_comments, created_at, permalink`

2. **`web/app.py:168-255`** - Raw Data Explorer 탭
   - `get_reddit_posts()` 호출하여 원본 테이블만 표시
   - Topic/Cluster 기반 뷰 없음

3. **현재 DB 상태 (2026-01-09 기준)**:
   ```sql
   -- raw_reddit_posts: 3,020개 posts 적재 완료 ✅
   -- clusters: 0개 (클러스터링 미실행)
   -- topic_qa_briefs: 0개 (LLM 라벨링 미실행)
   -- raw_serp_aio: 0개 (SERP 수집 미실행)
   ```

4. **기존 파이프라인 코드는 존재하지만 미실행**:
   - `worker/run_pipeline.py`: collect/analyze/label 모드 구현됨
   - `worker/pipeline/clustering.py`: HDBSCAN 클러스터링 구현됨
   - `worker/pipeline/labeling.py`: LLM 기반 brief 생성 구현됨
   - 하지만 실제 실행되지 않아서 `clusters`, `topic_qa_briefs` 테이블이 비어있음

### 결론

대시보드가 원본만 보여주는 이유:
- **데이터 부족**: 클러스터링/LLM 라벨링 결과가 아직 생성되지 않음
- **쿼리 구조**: `get_reddit_posts()`가 `raw_reddit_posts`만 조회
- **뷰 부재**: Topic/Cluster 중심 뷰가 구현되지 않음

---

## (B) 목표 스키마: Topic/Keyword/Cluster 레이어 추가

### 현재 스키마 (`migrations/001_initial_schema.sql` 기준)

**Raw 레벨 (이미 존재)**:
- `raw_reddit_posts`: 원본 Reddit 포스트
- `raw_serp_aio`: SERP AI Overview 스냅샷
- `raw_gsc_queries`: GSC 쿼리 데이터

**파생 레벨 (일부 존재)**:
- `clusters`: 클러스터 메타데이터 ✅
- `cluster_assignments`: 문서-클러스터 매핑 ✅
- `embeddings`: 임베딩 벡터 ✅
- `topic_qa_briefs`: LLM 생성 brief ✅
- `cluster_timeseries`: 월별 시계열 ✅

### 추가/수정 필요한 테이블

#### 옵션 1: raw_posts에 derived 컬럼 추가 (비권장)
- 장점: 조인 없이 빠른 조회
- 단점: 재처리/버전 관리 어려움, 스키마 변경 필요

#### 옵션 2: 별도 derived 테이블 (권장) ✅

**1. `keyword_index` 테이블 (신규)**
```sql
CREATE TABLE keyword_index (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(200) NOT NULL,
    source VARCHAR(50) NOT NULL, -- 'reddit', 'serp', 'gsc'
    topic_id INTEGER, -- NULL 가능 (아직 매핑 안 된 경우)
    cluster_id INTEGER, -- NULL 가능
    frequency INTEGER NOT NULL DEFAULT 0, -- 빈도
    weighted_score NUMERIC(10, 2) DEFAULT 0, -- upvotes/comments 가중치
    first_seen_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_keyword_index_keyword_source_run UNIQUE (keyword, source, created_from_run_id),
    CONSTRAINT fk_keyword_index_topic FOREIGN KEY (topic_id) 
        REFERENCES topic_qa_briefs(id) ON DELETE SET NULL,
    CONSTRAINT fk_keyword_index_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE SET NULL,
    CONSTRAINT fk_keyword_index_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_keyword_index_keyword ON keyword_index(keyword);
CREATE INDEX idx_keyword_index_topic_id ON keyword_index(topic_id) WHERE topic_id IS NOT NULL;
CREATE INDEX idx_keyword_index_cluster_id ON keyword_index(cluster_id) WHERE cluster_id IS NOT NULL;
CREATE INDEX idx_keyword_index_weighted_score ON keyword_index(weighted_score DESC);
```

**2. `serp_results` 테이블 (신규, `raw_serp_aio`와 별도)**
```sql
CREATE TABLE serp_results (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(500) NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    source_engine VARCHAR(50) DEFAULT 'google',
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dedup_hash VARCHAR(64) NOT NULL, -- SHA-256(url + keyword)
    raw_json JSONB,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_serp_results_dedup_hash UNIQUE (dedup_hash),
    CONSTRAINT fk_serp_results_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_serp_results_keyword ON serp_results(keyword);
CREATE INDEX idx_serp_results_url ON serp_results(url);
CREATE INDEX idx_serp_results_fetched_at ON serp_results(fetched_at DESC);
```

**3. `topics` 테이블 (신규, `topic_qa_briefs`와 별도 관리)**
```sql
CREATE TABLE topics (
    topic_id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    label VARCHAR(500) NOT NULL, -- GPT 생성 주제명
    description TEXT,
    representative_keywords JSONB, -- 대표 키워드 배열
    category VARCHAR(50) NOT NULL, -- 4개 대주제 중 하나
    model_version VARCHAR(50) NOT NULL,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_topics_cluster_model UNIQUE (cluster_id, model_version),
    CONSTRAINT fk_topics_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT fk_topics_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    CONSTRAINT chk_topics_category CHECK (category IN (
        'SPRING_RECIPES',
        'SPRING_KITCHEN_STYLING',
        'REFRIGERATOR_ORGANIZATION',
        'VEGETABLE_PREP_HANDLING'
    ))
);

CREATE INDEX idx_topics_cluster_id ON topics(cluster_id);
CREATE INDEX idx_topics_category ON topics(category);
CREATE INDEX idx_topics_label ON topics(label);
```

**4. `insights` 테이블 (신규, GPT 인사이트 저장)**
```sql
CREATE TABLE insights (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    period VARCHAR(20), -- 'weekly', 'monthly', 'quarterly'
    gpt_summary TEXT NOT NULL,
    recommendations JSONB, -- 추천 액션 배열
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50) NOT NULL,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_insights_topic FOREIGN KEY (topic_id) 
        REFERENCES topics(topic_id) ON DELETE CASCADE,
    CONSTRAINT fk_insights_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_insights_topic_id ON insights(topic_id);
CREATE INDEX idx_insights_generated_at ON insights(generated_at DESC);
```

**5. `post_topics` 테이블 (신규, Post-Topic 매핑)**
```sql
CREATE TABLE post_topics (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(50) NOT NULL, -- reddit_post_id
    topic_id INTEGER NOT NULL,
    cluster_id INTEGER NOT NULL,
    keywords JSONB, -- 이 포스트에서 추출된 키워드
    embedding JSONB, -- 임베딩 벡터 (참조용)
    scored_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_post_topics_post_topic_run UNIQUE (post_id, topic_id, created_from_run_id),
    CONSTRAINT fk_post_topics_post FOREIGN KEY (post_id) 
        REFERENCES raw_reddit_posts(reddit_post_id) ON DELETE CASCADE,
    CONSTRAINT fk_post_topics_topic FOREIGN KEY (topic_id) 
        REFERENCES topics(topic_id) ON DELETE CASCADE,
    CONSTRAINT fk_post_topics_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT fk_post_topics_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_post_topics_post_id ON post_topics(post_id);
CREATE INDEX idx_post_topics_topic_id ON post_topics(topic_id);
CREATE INDEX idx_post_topics_cluster_id ON post_topics(cluster_id);
```

### 마이그레이션 계획

**단계 1**: 기존 테이블 확인 및 데이터 백업
```sql
-- 기존 데이터 확인
SELECT COUNT(*) FROM raw_reddit_posts;
SELECT COUNT(*) FROM clusters;
SELECT COUNT(*) FROM topic_qa_briefs;
```

**단계 2**: 신규 테이블 생성 (마이그레이션 파일)
- `migrations/002_add_topic_keyword_tables.sql` 생성
- 위의 CREATE TABLE 문 실행

**단계 3**: 기존 데이터 마이그레이션
- `topic_qa_briefs` → `topics` (1:1 매핑)
- `cluster_assignments` → `post_topics` (매핑)
- Reddit posts에서 키워드 추출 → `keyword_index`

---

## (C) 파이프라인 잡 설계: Step 1~4

### Step 1: Reddit → Keyword 후보 추출

**입력**: `raw_reddit_posts` 테이블
**출력**: `keyword_index` 테이블

**구현 위치**: `worker/pipeline/keywords.py` (기존 파일 확장)

**알고리즘**:
1. TF-IDF 기반 키워드 추출 (기존 `extract_keywords_for_cluster` 활용)
2. Upvotes/Comments 가중치 적용:
   ```python
   weighted_score = log1p(upvotes) + 0.5 * log1p(num_comments)
   keyword_weight = tfidf_score * weighted_score
   ```
3. N-gram 추출 (1-gram, 2-gram): `TfidfVectorizer(ngram_range=(1, 2))`
4. 중복/일반 키워드 제거:
   - Stop words 제거 (영어 기본)
   - 너무 짧은 키워드 제거 (< 3자)
   - 너무 일반적인 키워드 제거 (예: "the", "and", "for")

**재실행 전략**:
- `(keyword, source='reddit', created_from_run_id)` UNIQUE 제약으로 upsert
- 동일 run_id로 재실행 시 중복 생성 방지

**스크립트**: `worker/pipeline/extract_keywords.py` (신규)

---

### Step 2: Keyword → SERP API 수집

**입력**: `keyword_index` 테이블 (상위 N개 키워드)
**출력**: `serp_results` 테이블

**구현 위치**: `worker/pipeline/collect_serp_aio.py` (기존 파일 확장)

**알고리즘**:
1. 키워드 선택:
   ```sql
   SELECT keyword, weighted_score 
   FROM keyword_index 
   WHERE source = 'reddit' 
   AND created_from_run_id = ?
   ORDER BY weighted_score DESC 
   LIMIT 50  -- 상위 50개만
   ```

2. 중복/일반 키워드 필터링:
   - 이미 `raw_serp_aio`에 있는 키워드 제외
   - 너무 일반적인 키워드 제외 (예: "kitchen", "recipe" 단독)

3. SerpAPI 호출:
   - 기존 `collect_serp_aio()` 함수 활용
   - AI Overview + 일반 검색 결과 모두 수집

4. 결과 저장:
   - `raw_serp_aio`: AI Overview (기존 테이블 유지)
   - `serp_results`: 일반 검색 결과 (신규 테이블)

5. 중복 제거:
   - `dedup_hash = SHA256(url + keyword)`로 중복 URL 제거
   - `(dedup_hash)` UNIQUE 제약으로 upsert

**재실행 전략**:
- `(dedup_hash)` UNIQUE 제약으로 upsert
- 동일 키워드로 재실행 시 중복 URL 자동 제거

**타임아웃/재시도**:
- SerpAPI 호출 타임아웃: 30초
- 재시도: 최대 3회, exponential backoff (1s, 2s, 4s)
- 네트워크 오류 시 실패 row 기록, 전체 중단하지 않음

**스크립트**: `worker/pipeline/collect_serp_results.py` (신규)

---

### Step 3: (Reddit + SERP) → Embedding/클러스터링

**입력**: 
- `raw_reddit_posts` (기존)
- `serp_results` (신규)

**출력**: 
- `embeddings` 테이블 (기존)
- `clusters` 테이블 (기존)
- `cluster_assignments` 테이블 (기존)

**텍스트 구성 정책**:
```python
# Reddit 포스트
text = f"{title}\n\n{body}" if body else title

# SERP 결과
text = f"{title}\n\n{snippet}" if snippet else title

# 통합 텍스트 (클러스터링용)
# Reddit과 SERP를 동일한 임베딩 공간에 배치
```

**임베딩 생성**:
- 기존 `worker/pipeline/embedding.py` 활용
- 모델: OpenAI `text-embedding-3-large` (기존과 동일)
- 배치 크기: 64 (기존과 동일)

**클러스터링**:
- 기존 `worker/pipeline/clustering.py` 활용
- 알고리즘: HDBSCAN (기존과 동일)
- 파라미터: `min_cluster_size=10`, `min_samples=5` (기존과 동일)

**선택 근거**:
- HDBSCAN: 클러스터 수 자동 결정, 노이즈 자동 식별
- Medoid 기준 대표 샘플: 실제 문서 기반으로 해석 가능성 높음

**재실행 전략**:
- `(doc_type, doc_id, created_from_run_id)` UNIQUE 제약으로 upsert
- 동일 run_id로 재실행 시 중복 생성 방지

---

### Step 4: 클러스터 → GPT 라벨링/요약/인사이트 생성

**입력**: `clusters` 테이블 (상위 N개 클러스터)
**출력**: 
- `topics` 테이블 (신규)
- `insights` 테이블 (신규)
- `topic_qa_briefs` 테이블 (기존, 유지)

**구현 위치**: `worker/pipeline/labeling.py` (기존 파일 확장)

**LLM 입력 구성**:
```python
prompt = f"""
클러스터 분석 요청:

대표 포스트 (Top 5):
{representative_posts}

특징 키워드:
{keywords[:15]}

월별 트렌드:
{monthly_trends_summary}

SERP 검색 결과 (Top 10):
{serp_results_summary}

다음 정보를 생성하세요:
1. 주제명 (label): 한 문장으로 요약
2. 설명 (description): 2-3문장 설명
3. 대표 키워드 (representative_keywords): Top 10
4. 인사이트 (insights): 콘텐츠/마케팅 관점 인사이트
5. 추천 액션 (recommendations): 실행 가능한 액션 3-5개
"""
```

**배치 처리**:
- 클러스터 단위로 LLM 호출 (기존과 동일)
- 배치 크기: 10개씩 (비용/속도 고려)
- 캐싱: 동일 클러스터 ID + 모델 버전으로 캐시

**비용 통제**:
- 상위 50개 클러스터만 LLM 호출 (기존 `MAX_BRIEFS_TO_GENERATE` 활용)
- 모델: `gpt-4o-mini` 또는 `gpt-3.5-turbo` (비용 절감)

**재실행 전략**:
- `(cluster_id, model_version)` UNIQUE 제약으로 upsert
- 동일 클러스터 + 모델 버전으로 재실행 시 업데이트

**스크립트**: `worker/pipeline/generate_insights.py` (신규)

---

## (D) 구현 변경 리스트

### 1. 마이그레이션 파일 생성

**파일**: `migrations/002_add_topic_keyword_tables.sql`
- `keyword_index` 테이블 생성
- `serp_results` 테이블 생성
- `topics` 테이블 생성
- `insights` 테이블 생성
- `post_topics` 테이블 생성
- 인덱스 및 제약조건 추가

### 2. 키워드 추출 모듈 확장

**파일**: `worker/pipeline/extract_keywords.py` (신규)
- 함수: `extract_keywords_from_posts(run_id, dry_run)`
- 입력: `raw_reddit_posts`
- 출력: `keyword_index` 테이블
- 변경: 기존 `keywords.py`의 `extract_keywords_for_cluster` 활용

### 3. SERP 수집 모듈 확장

**파일**: `worker/pipeline/collect_serp_results.py` (신규)
- 함수: `collect_serp_results_from_keywords(run_id, max_keywords=50, dry_run=False)`
- 입력: `keyword_index` 테이블
- 출력: `serp_results` 테이블
- 변경: 기존 `collect_serp_aio.py` 확장

### 4. 임베딩/클러스터링 모듈 확장

**파일**: `worker/pipeline/embedding.py` (수정)
- 함수: `generate_embeddings_for_serp(run_id, dry_run)` (신규)
- SERP 결과도 임베딩 생성

**파일**: `worker/pipeline/clustering.py` (수정)
- Reddit + SERP 통합 클러스터링 지원

### 5. 인사이트 생성 모듈

**파일**: `worker/pipeline/generate_insights.py` (신규)
- 함수: `generate_topic_insights(run_id, max_topics=50, dry_run=False)`
- 입력: `clusters` 테이블
- 출력: `topics`, `insights` 테이블

### 6. 파이프라인 실행 스크립트 수정

**파일**: `worker/run_pipeline.py` (수정)
- `--mode=extract_keywords`: Step 1 실행
- `--mode=collect_serp`: Step 2 실행 (기존 collect 모드 확장)
- `--mode=analyze`: Step 3 실행 (기존과 동일, SERP 포함)
- `--mode=generate_insights`: Step 4 실행 (기존 label 모드 확장)

### 7. 대시보드 쿼리 함수 추가

**파일**: `web/db_queries.py` (수정)
- 함수: `get_topics_list()` (신규)
- 함수: `get_topic_detail(topic_id)` (신규)
- 함수: `get_keyword_trends(keyword, period)` (신규)
- 함수: `get_pipeline_status()` (신규)

### 8. 대시보드 UI 수정

**파일**: `web/app.py` (수정)
- 탭 추가: "Topic Explorer" (신규)
- 탭 수정: "Raw Data Explorer" → "Topic 중심" 뷰 추가
- 위젯 추가: 키워드 트렌드 차트, 파이프라인 상태

---

## (E) 대시보드 변경: 쿼리/뷰/엔드포인트

### 1. Topic 리스트 뷰

**쿼리** (`web/db_queries.py`):
```python
def get_topics_list(category_filter=None, limit=100):
    query = """
        SELECT 
            t.topic_id,
            t.label,
            t.category,
            t.representative_keywords,
            COUNT(DISTINCT pt.post_id) as post_count,
            MAX(pt.scored_at) as last_updated
        FROM topics t
        LEFT JOIN post_topics pt ON t.topic_id = pt.topic_id
        WHERE 1=1
    """
    # category_filter 적용
    # ORDER BY post_count DESC
    # LIMIT
```

**UI** (`web/app.py`):
- 카드 리스트 형태로 표시
- 각 카드: label, category, 대표 키워드, 포스트 수, 최근 업데이트

### 2. Topic 상세 뷰

**쿼리**:
```python
def get_topic_detail(topic_id):
    query = """
        SELECT 
            t.*,
            i.gpt_summary,
            i.recommendations,
            -- 대표 포스트 Top 10
            -- 대표 SERP 링크 Top 10
        FROM topics t
        LEFT JOIN insights i ON t.topic_id = i.topic_id
        WHERE t.topic_id = %s
    """
```

**UI**:
- 대표 포스트 Top 10 (업보트/댓글 기준)
- 대표 SERP 링크 Top 10
- GPT 요약/추천 액션 표시

### 3. Keyword 트렌드

**쿼리**:
```python
def get_keyword_trends(keyword, period='monthly'):
    query = """
        SELECT 
            DATE_TRUNC('month', first_seen_at) as month,
            SUM(frequency) as total_frequency,
            AVG(weighted_score) as avg_score
        FROM keyword_index
        WHERE keyword = %s
        GROUP BY month
        ORDER BY month DESC
    """
```

**UI**:
- 키워드 빈도/가중치 추세 차트 (Plotly)
- SERP 수집 여부/최근 수집일 표시

### 4. 파이프라인 상태

**쿼리**:
```python
def get_pipeline_status():
    query = """
        SELECT 
            run_id,
            run_type,
            status,
            started_at,
            completed_at,
            metadata->>'total_posts' as total_posts,
            metadata->>'clusters_created' as clusters_created
        FROM pipeline_runs
        ORDER BY started_at DESC
        LIMIT 10
    """
```

**UI**:
- 마지막 배치 실행 시간
- 처리 건수, 실패 건수, 재시도 횟수

---

## (F) 실행 가이드

### 로컬 실행

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 환경 변수 설정
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="..."
export SERPAPI_KEY="..."

# Step 1: 키워드 추출
python3 worker/run_pipeline.py --mode=extract_keywords

# Step 2: SERP 수집
python3 worker/run_pipeline.py --mode=collect_serp --max-keywords=50

# Step 3: 임베딩/클러스터링
python3 worker/run_pipeline.py --mode=analyze --max-docs=1000

# Step 4: 인사이트 생성
python3 worker/run_pipeline.py --mode=generate_insights --max-topics=50

# 전체 실행
python3 worker/run_pipeline.py --mode=all
```

### Railway 실행

**One-off 실행**:
```bash
railway run python3 worker/run_pipeline.py --mode=extract_keywords
railway run python3 worker/run_pipeline.py --mode=collect_serp
railway run python3 worker/run_pipeline.py --mode=analyze
railway run python3 worker/run_pipeline.py --mode=generate_insights
```

**Worker 서비스로 실행**:
- `railway-worker.json`의 start command 수정:
  ```json
  {
    "deploy": {
      "startCommand": "python3 worker/run_pipeline.py --mode=all"
    }
  }
  ```

---

## (G) 리스크와 완화

### 1. 비용 (GPT/Embedding)

**리스크**:
- OpenAI API 비용: 임베딩 + LLM 호출
- SerpAPI 비용: 키워드당 $0.05 (예상)

**완화**:
- `--max-docs` 옵션으로 처리 문서 수 제한
- `--max-topics` 옵션으로 LLM 호출 수 제한
- 배치 크기 최적화 (64개씩)
- 캐싱으로 재호출 방지

**예상 비용**:
- 임베딩 (1,000개): ~$0.10
- LLM 호출 (50개 클러스터): ~$2-5
- SERP 수집 (50개 키워드): ~$2.50
- **총 예상**: ~$5-8 per run

### 2. 품질 (클러스터 품질)

**리스크**:
- 클러스터 수가 너무 많거나 적음
- 노이즈 비율이 높음
- 클러스터 간 중복

**완화**:
- HDBSCAN 파라미터 튜닝 (`min_cluster_size`, `min_samples`)
- 클러스터 품질 지표 측정:
  - Silhouette Score
  - 클러스터 간 평균 거리
- 수동 검증 샘플 제공

**측정 지표**:
```python
# 클러스터 품질 지표
- 총 클러스터 수: 50-200개 (목표)
- 노이즈 비율: < 30%
- 평균 클러스터 크기: 5-50개
- 클러스터 간 평균 거리: 최대화
```

### 3. 운영 (재시도/락)

**리스크**:
- DB 락으로 인한 hang
- 네트워크 타임아웃
- 부분 실패 시 복구

**완화**:
- 타임아웃 설정 (connect: 10s, statement: 60s)
- 재시도 로직 (최대 3회, exponential backoff)
- 실패 row 격리 (별도 테이블 기록)
- 배치 단위 트랜잭션 (너무 큰 트랜잭션 금지)

**모니터링**:
- `pipeline_runs` 테이블에 실행 상태 기록
- 실패 시 `error_message` 필드에 상세 로그
- 진행률 로그 (100건마다)

---

## 다음 단계

1. **마이그레이션 실행**: `migrations/002_add_topic_keyword_tables.sql` 실행
2. **키워드 추출 모듈 구현**: `worker/pipeline/extract_keywords.py` 작성
3. **SERP 수집 모듈 확장**: `worker/pipeline/collect_serp_results.py` 작성
4. **대시보드 쿼리 추가**: `web/db_queries.py`에 Topic 관련 함수 추가
5. **대시보드 UI 수정**: `web/app.py`에 Topic Explorer 탭 추가
6. **테스트 실행**: 로컬에서 전체 파이프라인 테스트
7. **Railway 배포**: 마이그레이션 실행 후 파이프라인 실행

---

**문서 버전**: 1.0  
**작성일**: 2026-01-09  
**기준**: SPEC.md, TASKS.md, 기존 구현 코드 분석
