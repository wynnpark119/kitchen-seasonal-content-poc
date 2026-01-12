# Analyze Mode 구현 완료 요약

## 구현된 모듈

### 1. `worker/pipeline/preprocess.py`
- ✅ 분석 텍스트 생성: `text = title + "\n\n" + body` (body 없으면 title만)
- ✅ 제거 규칙: title 비어있음, 30자 이하, 삭제된 글 (`[deleted]`, `[removed]`)
- ✅ 중복 제거: `text_hash` (SHA-256)로 동일 텍스트 중복 제거
- ✅ 중복 시 우선순위: `upvotes + num_comments` 높은 것 선택
- ✅ 비용 통제: `--max-docs` 옵션으로 상위 반응 포스트만 처리

### 2. `worker/pipeline/embedding.py`
- ✅ OpenAI `text-embedding-3-large` 사용 (dim=3072)
- ✅ 배치 처리 (batch_size=64)
- ✅ Retry/backoff (최대 3회, exponential backoff)
- ✅ pgvector 자동 감지 (`check_pgvector_available()`)
- ✅ JSONB 저장 (pgvector 없을 때)
- ✅ `(doc_type, doc_id, created_from_run_id)` UNIQUE 제약으로 upsert

### 3. `worker/pipeline/clustering.py`
- ✅ HDBSCAN 클러스터링
- ✅ **Medoid 기준 대표 샘플 선정** (centroid 대신)
- ✅ `clusters` 테이블: 클러스터 메타 저장
- ✅ `cluster_assignments` 테이블: 문서-클러스터 매핑
- ✅ `is_representative=true`: Medoid 기준 top-k (기본 5개)
- ✅ `distance_to_centroid`: Medoid 기준 거리 저장

### 4. `worker/pipeline/db.py`
- ✅ `check_pgvector_available()`: pgvector 자동 감지
- ✅ `upsert_embedding()`: pgvector/JSONB 자동 분기
- ✅ 모든 upsert 함수 구현

### 5. `worker/pipeline/config.py`
- ✅ `MIN_TEXT_LENGTH = 30`
- ✅ `EMBEDDING_BATCH_SIZE = 64`
- ✅ `HDBSCAN_MIN_CLUSTER_SIZE = 10`
- ✅ `HDBSCAN_MIN_SAMPLES = 5`
- ✅ `REPRESENTATIVE_SAMPLES_K = 5`

### 6. `worker/run_pipeline.py`
- ✅ `--mode=analyze` 연결 완료
- ✅ `--dry-run` 옵션 지원
- ✅ `--max-docs` 옵션 추가 (비용 통제)
- ✅ 순서: preprocess → embedding → clustering
- ✅ 실행 예시 주석 포함

---

## 실행 커맨드

### Dry-run (샘플 10개만)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze --dry-run
```

### 실제 실행 (전체)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze
```

### 비용 통제 (상위 100개만)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=analyze --max-docs=100
```

---

## 주요 특징

### Medoid 기준 대표 샘플
- **Centroid 대신 Medoid 사용**: HDBSCAN은 centroid를 제공하지 않으므로, 클러스터 내 평균 거리가 최소인 문서(medoid)를 기준으로 사용
- **해석 가능성**: Medoid는 실제 문서이므로 해석이 용이
- **대표 샘플 선정**: Medoid 기준으로 가장 가까운 k개 문서를 대표 샘플로 선정

### 중복 제거 로직
- `text_hash` (SHA-256)로 동일 텍스트 식별
- 중복 시 `upvotes + num_comments` 높은 것 우선 선택
- DB에 이미 존재하는 hash는 스킵

### pgvector 자동 감지
- `check_pgvector_available()` 함수로 pgvector 사용 가능 여부 자동 감지
- pgvector 없으면 JSONB로 저장 (현재 DDL 기준 JSONB 사용)

### 재실행 안정성
- 모든 쓰기 작업은 upsert/unique key 기반
- 동일 run_id로 재실행해도 중복 생성되지 않음
- `pipeline_runs` 테이블에 실행 상태/에러/처리 건수 기록

---

## 검증 SQL

### 1. Preprocessing 결과

```sql
-- 전처리 통계 (수동 계산 필요)
SELECT 
    COUNT(*) as total_posts,
    COUNT(DISTINCT reddit_post_id) as unique_posts
FROM raw_reddit_posts;
```

### 2. Embedding 확인

```sql
-- 임베딩 통계
SELECT 
    COUNT(*) as total_embeddings,
    COUNT(DISTINCT doc_id) as unique_docs,
    AVG(jsonb_array_length(embedding_json)) as avg_dimension,
    MIN(jsonb_array_length(embedding_json)) as min_dim,
    MAX(jsonb_array_length(embedding_json)) as max_dim
FROM embeddings
WHERE doc_type = 'reddit_post'
AND created_from_run_id = ?;
```

### 3. Clustering 결과

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

-- Noise 비율
SELECT 
    (SELECT COUNT(*) FROM cluster_assignments WHERE created_from_run_id = ?) as total_points,
    (SELECT COUNT(*) FROM clusters WHERE noise_label = TRUE AND created_from_run_id = ?) as noise_clusters;

-- Medoid 기준 대표 샘플
SELECT 
    c.cluster_id,
    c.size,
    COUNT(ca.id) FILTER (WHERE ca.is_representative = TRUE) as representative_count,
    AVG(ca.distance_to_centroid) FILTER (WHERE ca.is_representative = TRUE) as avg_medoid_distance
FROM clusters c
LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
WHERE c.created_from_run_id = ?
AND c.noise_label = FALSE
GROUP BY c.cluster_id, c.size
ORDER BY c.size DESC
LIMIT 10;
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
- [ ] pgvector 자동 감지 작동
- [ ] 모든 embedding에 `created_from_run_id` 연결됨

### ✅ Clustering
- [ ] 클러스터 생성됨 (clusters 테이블에 데이터 존재)
- [ ] Cluster assignments 생성됨
- [ ] **Medoid 기준 대표 샘플 선정됨** (is_representative=true)
- [ ] Noise 비율 로그 출력됨

---

## 다음 단계

Analyze 모드 완료 후:
- `--mode=label`: LLM 기반 클러스터 해석 및 brief 생성
- `--mode=all`: 전체 파이프라인 실행
