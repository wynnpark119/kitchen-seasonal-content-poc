# Analyze Mode 실행 가이드

## 목표
Reddit raw 데이터에서 분석용 텍스트 생성 → OpenAI 임베딩 생성 → HDBSCAN 클러스터링 → 대표 샘플 선정

---

## 실행 커맨드

### 1. Dry-run (샘플 처리만)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key" \
python3 worker/run_pipeline.py --mode=analyze --dry-run
```

**예상 출력:**
- Preprocessing: 샘플 10개 표시
- Embedding: 배치 처리 시뮬레이션
- Clustering: 클러스터링 시뮬레이션

### 2. 실제 실행

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key" \
python3 worker/run_pipeline.py --mode=analyze
```

---

## 처리 단계

### Step 1: Preprocessing
- **입력**: `raw_reddit_posts` 테이블
- **처리**:
  - 분석용 텍스트 생성: `text = title + "\n\n" + body` (body 없으면 title만)
  - 제거: 30자 이하, 삭제된 글 (`[deleted]`, `[removed]`)
  - 중복 제거: `text_hash` (SHA-256)로 동일 텍스트 스킵
- **출력**: 통계 (cleaned_posts, duplicates_removed 등)

### Step 2: Embedding Generation
- **입력**: Preprocessing된 포스트
- **처리**:
  - OpenAI `text-embedding-3-large` 사용
  - 배치 처리 (batch_size=64)
  - Retry/backoff (최대 3회)
- **출력**: `embeddings` 테이블에 저장
  - `(doc_type='reddit_post', doc_id, created_from_run_id)` UNIQUE
  - `embedding_json` (JSONB): 임베딩 벡터 배열

### Step 3: Clustering
- **입력**: `embeddings` 테이블 (해당 run_id)
- **처리**:
  - HDBSCAN 클러스터링
  - Centroid 계산
  - 대표 샘플 선정 (centroid 기준 top-k, 기본 5개)
- **출력**:
  - `clusters` 테이블: 클러스터 메타
  - `cluster_assignments` 테이블: 문서-클러스터 매핑
  - `is_representative=true`: 대표 샘플 플래그

---

## 검증 SQL

### 1. Preprocessing 결과 확인

```sql
-- 총 포스트 수
SELECT COUNT(*) FROM raw_reddit_posts;

-- 임베딩 생성된 포스트 수
SELECT COUNT(DISTINCT doc_id) 
FROM embeddings 
WHERE doc_type = 'reddit_post' 
AND created_from_run_id = ?;
```

### 2. Embedding 확인

```sql
-- 임베딩 통계
SELECT 
    COUNT(*) as total_embeddings,
    COUNT(DISTINCT doc_id) as unique_docs,
    AVG(jsonb_array_length(embedding_json)) as avg_dimension
FROM embeddings
WHERE doc_type = 'reddit_post'
AND created_from_run_id = ?;

-- 샘플 임베딩 확인
SELECT doc_id, jsonb_array_length(embedding_json) as dim, created_at
FROM embeddings
WHERE doc_type = 'reddit_post'
AND created_from_run_id = ?
LIMIT 5;
```

### 3. Clustering 결과 확인

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

-- 대표 샘플 확인
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

### 4. 클러스터별 대표 샘플 조회

```sql
SELECT 
    ca.cluster_id,
    ca.doc_id,
    ca.distance_to_centroid,
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
- [ ] Cleaned posts > 0
- [ ] Duplicates removed 기록됨

### ✅ Embedding
- [ ] Embeddings 생성됨 (embeddings 테이블에 데이터 존재)
- [ ] Dimension = 3072 (text-embedding-3-large)
- [ ] 모든 embedding에 `created_from_run_id` 연결됨

### ✅ Clustering
- [ ] 클러스터 생성됨 (clusters 테이블에 데이터 존재)
- [ ] Cluster assignments 생성됨
- [ ] 대표 샘플 선정됨 (is_representative=true)
- [ ] Noise 비율 로그 출력됨

---

## 예상 실행 시간

- **Preprocessing**: ~1-5초 (데이터 크기에 따라)
- **Embedding**: ~10-30초 (100개 포스트 기준, 배치 처리)
- **Clustering**: ~5-10초 (HDBSCAN 실행)

**총 예상 시간**: ~20-45초 (100개 포스트 기준)

---

## 주의사항

1. **OpenAI API 키 필요**: `OPENAI_API_KEY` 환경변수 필수
2. **비용**: text-embedding-3-large는 유료 모델입니다
3. **배치 처리**: 배치 크기 64로 최적화되어 있음
4. **중복 제거**: text_hash로 동일 텍스트는 스킵됨

---

## 다음 단계

Analyze 모드 완료 후:
- `--mode=label`: LLM 기반 클러스터 해석 및 brief 생성
- `--mode=all`: 전체 파이프라인 실행
