# 임베딩 코드 비활성화 안내

## 비활성화 대상

다음 파일/함수는 **Post 단위 임베딩**을 수행하므로 비활성화되었습니다.

### 1. `worker/pipeline/embedding.py`

**비활성화 함수**:
- `generate_embeddings()` - Post 단위 임베딩 생성 (라인 122-332)
- `generate_embeddings_batch()` - 배치 임베딩 (라인 67-91)

**유지 함수**:
- `truncate_text_to_max_tokens()` - 클러스터 임베딩에서 재사용 (라인 30-65)

**대체**: `worker/pipeline/cluster_embedding.py` 사용

### 2. `worker/pipeline/clustering.py`

**비활성화 함수**:
- `load_embeddings()` - 임베딩 로드 (라인 17-57)
- `run_clustering()` - HDBSCAN 클러스터링 (라인 59-81)

**유지 함수**:
- `upsert_cluster_assignment()` - 클러스터 할당 저장 (재사용)

**대체**: `worker/pipeline/tfidf_clustering.py` 사용

### 3. `worker/run_pipeline.py`

**비활성화 코드**:
- `run_analyze_mode()` 내 `generate_embeddings()` 호출 (라인 166)
- `run_clustering_pipeline()` 호출 (라인 176)

**대체**: 새로운 모드 사용
- `--mode=cluster_tfidf`: TF-IDF 클러스터링
- `--mode=embed_clusters`: 클러스터 요약 임베딩

### 4. `scripts/retry_failed_embeddings.py`

**전체 파일 비활성화**: Post 단위 재처리 스크립트 (더 이상 사용 안 함)

## 새로운 임베딩 방식

**파일**: `worker/pipeline/cluster_embedding.py`

**임베딩 대상**:
- 클러스터 요약 텍스트 (3~5줄)
- 대표 키워드 (Top 20)
- 대표 SERP snippet 일부 (선택적)

**사용법**:
```bash
python worker/run_pipeline.py --mode=embed_clusters
```

## 마이그레이션 가이드

기존 Post 단위 임베딩 데이터는 그대로 유지되지만, 새로운 파이프라인에서는 사용하지 않습니다.

새로운 파이프라인을 실행하면:
1. TF-IDF 기반으로 4개 클러스터 생성
2. 클러스터 요약만 임베딩 생성 (`cluster_embeddings` 테이블)

기존 `embeddings` 테이블의 Post 단위 임베딩은 참고용으로만 사용 가능합니다.
