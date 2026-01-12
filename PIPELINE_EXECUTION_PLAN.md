# 전체 파이프라인 실행 계획

## 현재 상태

### ✅ 완료된 작업
1. **데이터 수집**: 20개 키워드의 Apify 데이터를 JSON 파일로 다운로드 완료
   - 위치: `data/` 폴더
   - 총 10,501개 아이템
   - 20개 JSON 파일 저장됨

### 🔄 다음 단계
1. JSON 파일을 DB에 적재
2. 데이터 전처리
3. 임베딩 생성
4. 클러스터링
5. 시계열 분석
6. LLM 기반 Brief 생성

---

## 전체 파이프라인 프로세스

### Phase 1: 데이터 적재 (Collect)
**목적**: JSON 파일을 PostgreSQL 데이터베이스에 적재

**실행 방법**:
```bash
export DATABASE_URL="postgresql://..."
export APIFY_API_TOKEN="apify_api_..."
python3 save_keywords_local.py
```

**처리 내용**:
- `data/*.json` 파일들을 읽어서 `raw_reddit_posts`와 `raw_reddit_comments` 테이블에 저장
- `process_apify_results.py`를 통해 데이터 파싱 및 정규화
- 배치 삽입으로 성능 최적화

**예상 결과**:
- 약 10,000개 이상의 Reddit 포스트 저장
- 각 포스트의 댓글도 함께 저장

---

### Phase 2: 데이터 전처리 (Preprocess)
**목적**: Raw 데이터를 분석 가능한 형태로 정제

**실행 방법**:
```bash
python worker/run_pipeline.py --mode=analyze
# 또는 개별 실행
python -c "from worker.pipeline.preprocess import preprocess_reddit_posts; preprocess_reddit_posts(run_id, dry_run=False)"
```

**처리 내용** (`worker/pipeline/preprocess.py`):
1. **텍스트 정제**:
   - HTML 태그 제거
   - 공백 정규화
   - 분석용 텍스트 생성: `title + "\n\n" + body`

2. **필터링**:
   - 삭제된 글 제거 (`[deleted]`, `[removed]`)
   - 너무 짧은 글 제거 (30자 이하)
   - 제목이 비어있는 글 제거

3. **중복 제거**:
   - `text_hash` (SHA-256) 기반 중복 제거
   - 중복 시 `upvotes + num_comments` 높은 것 우선

4. **결과 저장**:
   - `reddit_posts_cleaned` 테이블에 저장
   - 또는 `raw_reddit_posts` 테이블의 `is_preprocessed` 플래그 업데이트

**예상 결과**:
- 약 8,000-9,000개 정제된 포스트 (중복 및 노이즈 제거 후)

---

### Phase 3: 임베딩 생성 (Embedding)
**목적**: 정제된 포스트에 대해 OpenAI 임베딩 생성

**실행 방법**:
```bash
python worker/run_pipeline.py --mode=analyze
# 또는 개별 실행
python -c "from worker.pipeline.embedding import generate_embeddings; generate_embeddings(run_id, dry_run=False)"
```

**처리 내용** (`worker/pipeline/embedding.py`):
1. **모델**: `text-embedding-3-large` (3072 차원)
2. **배치 처리**: 64개씩 배치로 처리 (비용 최적화)
3. **재시도 로직**: API 실패 시 최대 3회 재시도 (exponential backoff)
4. **중복 방지**: 이미 임베딩이 있으면 스킵
5. **저장**: `embeddings` 테이블에 JSONB 형식으로 저장

**비용 예상**:
- 약 8,000개 포스트 × $0.00013/1K tokens ≈ $10-20 (대략)

**예상 결과**:
- 모든 정제된 포스트에 대한 임베딩 벡터 생성 완료

---

### Phase 4: 클러스터링 (Clustering)
**목적**: 유사한 포스트들을 클러스터로 그룹화

**실행 방법**:
```bash
python worker/run_pipeline.py --mode=analyze
# 또는 개별 실행
python -c "from worker.pipeline.clustering import run_clustering_pipeline; run_clustering_pipeline(run_id, dry_run=False)"
```

**처리 내용** (`worker/pipeline/clustering.py`):
1. **알고리즘**: HDBSCAN
   - `min_cluster_size`: 10
   - `min_samples`: 5
   - `metric`: 'euclidean'

2. **클러스터 생성**:
   - 유사한 포스트들을 그룹화
   - Noise 포인트는 별도 처리

3. **대표 샘플 선정**:
   - Medoid 기준으로 클러스터 내 대표 샘플 선정
   - 각 클러스터당 최대 5개 대표 샘플

4. **저장**:
   - `clusters` 테이블: 클러스터 메타데이터
   - `cluster_assignments` 테이블: 포스트-클러스터 매핑

**예상 결과**:
- 약 50-200개 클러스터 생성
- 각 클러스터당 평균 10-50개 포스트

---

### Phase 5: 특징어 추출 및 시계열 분석
**목적**: 클러스터의 특징어 추출 및 월별 트렌드 분석

**실행 방법**:
```bash
python worker/run_pipeline.py --mode=analyze
```

**처리 내용**:
1. **특징어 추출** (`worker/pipeline/keywords.py`):
   - TF-IDF 기반 특징어 추출
   - 각 클러스터당 상위 15개 키워드

2. **시계열 생성** (`worker/pipeline/timeseries.py`):
   - 월별 집계: `created_utc`를 YYYY-MM 형식으로 변환
   - Reddit 가중 점수 계산: `upvotes + num_comments * 2`
   - 카테고리별 시즌성 해석:
     - **Seasonal** (SPRING_RECIPES, SPRING_KITCHEN_STYLING): 봄 시즌 대비 성장률
     - **Evergreen** (REFRIGERATOR_ORGANIZATION, VEGETABLE_PREP_HANDLING): 절대 성장률

3. **저장**:
   - `cluster_keywords` 테이블: 특징어 저장
   - `cluster_timeseries` 테이블: 월별 트렌드 저장

**예상 결과**:
- 각 클러스터의 특징어 및 월별 트렌드 데이터 생성 완료

---

### Phase 6: LLM 기반 Brief 생성 (Label)
**목적**: 클러스터 단위로 LLM을 호출하여 콘텐츠 기획용 Brief 생성

**실행 방법**:
```bash
python worker/run_pipeline.py --mode=label --max-briefs=50
```

**처리 내용** (`worker/pipeline/labeling.py`):
1. **LLM 모델**: `gpt-4o-mini` (비용 최적화)
2. **입력 구성**:
   - 클러스터 대표 샘플 (최대 5개)
   - 특징어 리스트
   - 월별 트렌드 요약
   - SERP AIO 요약 (있는 경우)
   - GSC 데이터 요약 (있는 경우)

3. **생성 항목**:
   - `category`: 4대 주제 카테고리
   - `topic_title`: 주제 제목
   - `primary_question`: 핵심 질문
   - `related_questions`: 관련 질문 리스트
   - `blog_angle`: 블로그 콘텐츠 각도
   - `social_angle`: 소셜 미디어 각도
   - `why_now`: 왜 지금인가 (트렌드, 드라이버, 예상 영향)
   - `evidence_pack`: 증거 패키지 (Reddit 포스트, SERP AIO, GSC 데이터)

4. **저장**:
   - `topic_qa_briefs` 테이블에 저장

**비용 예상**:
- 약 50개 클러스터 × $0.15/1K tokens ≈ $5-10 (대략)

**예상 결과**:
- 약 50개의 콘텐츠 기획용 Brief 생성 완료

---

### Phase 7: 점수 계산 (Scoring)
**목적**: Brief에 우선순위 점수 부여

**실행 방법**:
```bash
python worker/run_pipeline.py --mode=label
```

**처리 내용** (`worker/pipeline/scoring.py`):
1. **점수 계산 요소**:
   - 클러스터 크기
   - 평균 업보트
   - 최근성 (최근 3개월 가중)
   - GSC 연관성 (있는 경우)
   - SERP AIO 존재 여부

2. **저장**:
   - `topic_qa_briefs` 테이블의 `score` 컬럼 업데이트

**예상 결과**:
- 각 Brief에 우선순위 점수 부여 완료

---

## 실행 순서 요약

### 1단계: 데이터 적재
```bash
export DATABASE_URL="postgresql://..."
export APIFY_API_TOKEN="apify_api_..."
python3 save_keywords_local.py
```

### 2단계: 전체 분석 파이프라인 실행
```bash
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."
python worker/run_pipeline.py --mode=analyze --max-docs=1000
```

**옵션**:
- `--max-docs=1000`: 비용 통제를 위해 상위 1000개만 처리 (선택사항)
- `--dry-run`: DB 쓰기 없이 테스트 (선택사항)

### 3단계: LLM Brief 생성
```bash
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."
python worker/run_pipeline.py --mode=label --max-briefs=50
```

### 4단계: 전체 파이프라인 한 번에 실행 (선택사항)
```bash
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."
export APIFY_API_TOKEN="apify_api_..."
python worker/run_pipeline.py --mode=all --max-docs=1000 --max-briefs=50
```

---

## 비용 예상

### OpenAI API 비용
- **임베딩**: 약 $10-20 (8,000개 포스트)
- **LLM Brief**: 약 $5-10 (50개 클러스터)
- **총 예상**: 약 $15-30

### Apify API 비용
- 이미 수집 완료 (JSON 파일로 저장됨)
- 추가 비용 없음

---

## 주의사항

1. **DATABASE_URL 설정 필수**: 모든 단계에서 필요
2. **OPENAI_API_KEY 설정**: Phase 3, 6에서 필요
3. **비용 통제**: `--max-docs` 옵션으로 처리량 제한 가능
4. **재실행 안전**: 모든 작업은 upsert 기반이므로 재실행 가능
5. **Dry Run 테스트**: `--dry-run` 옵션으로 먼저 테스트 권장

---

## 다음 단계

1. ✅ JSON 파일 다운로드 완료
2. ⏳ DATABASE_URL 설정 후 데이터 적재
3. ⏳ 전처리 및 임베딩 생성
4. ⏳ 클러스터링 및 시계열 분석
5. ⏳ LLM Brief 생성
6. ⏳ Streamlit 대시보드에서 결과 확인
