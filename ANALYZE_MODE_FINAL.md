# Analyze Mode 최종 구현 가이드

## 목표
Reddit 포스트 텍스트 임베딩 생성 → HDBSCAN 클러스터링 → Medoid 기준 대표 샘플 선정

---

## 주요 구현 사항

### 1. Preprocessing (`worker/pipeline/preprocess.py`)
- ✅ 분석 텍스트 생성: `text = title + "\n\n" + body` (body 없으면 title만)
- ✅ 제거 규칙: title 비어있음, 30자 이하, 삭제된 글
- ✅ 중복 제거: `text_hash` (SHA-256)로 동일 텍스트 중복 제거
- ✅ 중복 시 우선순위: `upvotes + num_comments` 높은 것 선택
- ✅ 비용 통제: `--max-docs` 옵션으로 상위 반응 포스트만 처리

### 2. Embedding (`worker/pipeline/embedding.py`)
- ✅ OpenAI `text-embedding-3-large` 사용 (dim=3072)
- ✅ 배치 처리 (batch_size=64)
- ✅ Retry/backoff (최대 3회)
- ✅ pgvector 자동 감지 및 분기 (JSONB 사용)
- ✅ `(doc_type, doc_id)` UNIQUE 제약으로 upsert

### 3. Clustering (`worker/pipeline/clustering.py`)
- ✅ HDBSCAN 클러스터링
- ✅ **Medoid 기준 대표 샘플 선정** (centroid 대신)
- ✅ `clusters` 테이블: 클러스터 메타 저장
- ✅ `cluster_assignments` 테이블: 문서-클러스터 매핑
- ✅ `is_representative=true`: Medoid 기준 top-k (기본 5개)

### 4. Database (`worker/pipeline/db.py`)
- ✅ `check_pgvector_available()`: pgvector 자동 감지
- ✅ `upsert_embedding()`: pgvector/JSONB 자동 분기

### 5. Config (`worker/pipeline/config.py`)
- ✅ `MIN_TEXT_LENGTH = 30`
- ✅ `EMBEDDING_BATCH_SIZE = 64`
- ✅ `HDBSCAN_MIN_CLUSTER_SIZE = 10`
- ✅ `HDBSCAN_MIN_SAMPLES = 5`

---

## 실행 커맨드

### 1. Dry-run (샘플 10개만)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze --dry-run
```

### 2. 실제 실행 (전체)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze
```

### 3. 비용 통제 (상위 100개만)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze --max-docs=100
```

---

## 처리 단계

### Step 1: Preprocessing
- 입력: `raw_reddit_posts` 테이블
- 처리:
  - 분석 텍스트 생성: `title + "\n\n" + body`
  - 제거: title 비어있음, 30자 이하, 삭제된 글
  - 중복 제거: `text_hash` 기준, `upvotes + num_comments` 높은 것 우선
- 출력: 전처리된 문서 리스트 (embedding 단계로 전달)

### Step 2: Embedding Generation
- 입력: Preprocessing된 포스트
- 처리:
  - OpenAI `text-embedding-3-large` 배치 처리 (64개씩)
  - Retry/backoff (최대 3회)
  - pgvector 자동 감지 (없으면 JSONB 사용)
- 출력: `embeddings` 테이블에 저장
  - `(doc_type='reddit_post', doc_id)` UNIQUE

### Step 3: Clustering
- 입력: `embeddings` 테이블 (해당 run_id)
- 처리:
  - HDBSCAN 클러스터링
  - **Medoid 계산** (클러스터 내 평균 거리 최소 문서)
  - 대표 샘플 선정 (medoid 기준 top-k, 기본 5개)
- 출력:
  - `clusters` 테이블: 클러스터 메타
  - `cluster_assignments` 테이블: 문서-클러스터 매핑
  - `is_representative=true`: Medoid 기준 대표 샘플

---

## Medoid vs Centroid

### Medoid 선택 이유
- HDBSCAN은 centroid를 기본 산출물로 제공하지 않음
- Medoid는 클러스터 내 실제 문서이므로 해석 가능성이 높음
- 평균 거리 기준으로 클러스터 중심을 잘 대표함

### 구현 방식
```python
# 각 클러스터마다:
1. 클러스터 내 모든 문서 간 거리 계산
2. 평균 거리가 최소인 문서 = Medoid
3. Medoid 기준으로 가장 가까운 k개 문서 = 대표 샘플
```

---

## 검증 SQL

### 1. Embedding 확인

```sql
-- 임베딩 통계
SELECT 
    COUNT(*) as total_embeddings,
    COUNT(DISTINCT doc_id) as unique_docs,
    AVG(jsonb_array_length(embedding_json)) as avg_dimension
FROM embeddings
WHERE doc_type = 'reddit_post'
AND created_from_run_id = ?;

-- pgvector 사용 여부 확인
SELECT EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'vector'
) as pgvector_available;
```

### 2. Clustering 결과 확인

```sql
-- 클러스터 통계
SELECT 
    COUNT(*) as total_clusters,
    SUM(size) as total_assignments,
    AVG(size) as avg_cluster_size,
    MIN(size) as min_size,
    MAX(size) as max_size
FROM clusters
WHERE created_from_run_id = ?
AND noise_label = FALSE;

-- Medoid 기준 대표 샘플 확인
SELECT 
    c.cluster_id,
    c.size,
    COUNT(ca.id) FILTER (WHERE ca.is_representative = TRUE) as representative_count
FROM clusters c
LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
WHERE c.created_from_run_id = ?
AND c.noise_label = FALSE
GROUP BY c.cluster_id, c.size
ORDER BY c.size DESC
LIMIT 10;
```

### 3. 대표 샘플 조회

```sql
SELECT 
    ca.cluster_id,
    ca.doc_id,
    ca.distance_to_centroid as medoid_distance,
    rp.title,
    LEFT(rp.body, 100) as body_preview
FROM cluster_assignments ca
JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
WHERE ca.is_representative = TRUE
AND ca.created_from_run_id = ?
ORDER BY ca.cluster_id, ca.distance_to_centroid
LIMIT 20;
```

---

## 완료 조건

### ✅ Preprocessing
- [ ] 총 포스트 수 확인
- [ ] Title empty, Too short, Deleted 필터링 완료
- [ ] 중복 제거 완료 (upvotes + num_comments 높은 것 우선)

### ✅ Embedding
- [ ] Embeddings 생성됨 (embeddings 테이블에 데이터 존재)
- [ ] Dimension = 3072 (text-embedding-3-large)
- [ ] pgvector 자동 감지 및 분기 작동
- [ ] 모든 embedding에 `created_from_run_id` 연결됨

### ✅ Clustering
- [ ] 클러스터 생성됨 (clusters 테이블에 데이터 존재)
- [ ] Cluster assignments 생성됨
- [ ] **Medoid 기준 대표 샘플 선정됨** (is_representative=true)
- [ ] Noise 비율 로그 출력됨

---

## 예상 실행 시간

- **Preprocessing**: ~1-5초 (데이터 크기에 따라)
- **Embedding**: 
  - 100개 포스트: ~10-20초
  - 1000개 포스트: ~2-3분
- **Clustering**: ~5-10초 (HDBSCAN 실행)

**총 예상 시간**: 
- 100개 포스트: ~20-35초
- 1000개 포스트: ~3-4분

---

## 주의사항

1. **OpenAI API 키 필요**: `OPENAI_API_KEY` 환경변수 필수
2. **비용**: text-embedding-3-large는 유료 모델입니다
3. **배치 처리**: 배치 크기 64로 최적화되어 있음
4. **중복 제거**: text_hash로 동일 텍스트는 스킵됨
5. **Medoid 사용**: Centroid 대신 Medoid 기준으로 대표 샘플 선정

---

## 다음 단계

Analyze 모드 완료 후:
- `--mode=label`: LLM 기반 클러스터 해석 및 brief 생성
- `--mode=all`: 전체 파이프라인 실행
