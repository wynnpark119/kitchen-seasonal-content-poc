# 클러스터링 결과 검증 리포트

생성일: 2026-01-09
검증 대상: topic_category별 클러스터링 구조 및 DB 저장 상태

---

## [1] 클러스터링 실행 단위 검증 (구조 검증)

### 코드 구조 분석

**파일**: `worker/pipeline/tfidf_clustering.py`

#### 카테고리별 데이터 분리 지점
- **라인 340-361**: 카테고리별로 포스트 분류
  ```python
  category_posts = {category: [] for category in CATEGORIES}
  
  for post_id, title, body, upvotes, num_comments, keyword in all_posts:
      # 삭제된 글 스킵
      if is_deleted_post(title, body):
          continue
      
      # 텍스트 추출
      post_text = extract_text_from_post(title, body)
      
      # 카테고리 할당
      category = assign_post_to_category(post_text, keyword)
      
      category_posts[category].append({...})
  ```

#### 카테고리별 독립 클러스터링 실행 지점
- **라인 374**: `for category in CATEGORIES:` ← **카테고리별 반복문**
- **라인 396**: `cluster_groups = cluster_posts_within_category(posts, category)` ← **각 카테고리별로 독립적으로 클러스터링 수행**

#### topic_category 저장 지점
- **라인 432-439**: params_json에 'topic_category' 저장
  ```python
  params = {
      "method": "tfidf_kmeans",
      "topic_category": category,  # ← 카테고리 정보 저장
      "sub_cluster_index": cluster_idx,
      "top_keywords": [kw for kw, _ in top_keywords],
      "representative_post_ids": [p['post_id'] for p in representative_posts],
      "summary": summary
  }
  ```

### 결론

✅ **클러스터링은 주제별로 분리되어 실행되었음**

**근거**:
1. 전체 Reddit 데이터를 한 번에 클러스터링하는 코드가 없음
2. `for category in CATEGORIES:` 반복문으로 각 카테고리별로 독립 실행
3. 각 카테고리 내에서만 `cluster_posts_within_category()` 호출
4. 각 클러스터의 `params_json`에 `topic_category` 저장

---

## [2] DB 저장 여부 및 스키마 검증

### 테이블 스키마

#### `clusters` 테이블
- `cluster_id` (SERIAL PRIMARY KEY)
- `algorithm` (VARCHAR) - 'TF-IDF_KMEANS' 또는 'TF-IDF_KEYWORD'
- `params_json` (JSONB) - **topic_category 저장 위치**
- `noise_label` (BOOLEAN)
- `size` (INTEGER) - 클러스터 내 포스트 수
- `created_from_run_id` (INTEGER)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

#### `cluster_assignments` 테이블
- `id` (SERIAL PRIMARY KEY)
- `cluster_id` (INTEGER) - clusters 테이블 참조
- `doc_type` (VARCHAR) - 'reddit_post'
- `doc_id` (VARCHAR) - reddit_post_id
- `distance_to_centroid` (NUMERIC)
- `is_representative` (BOOLEAN)
- `created_from_run_id` (INTEGER)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### topic_category 저장 구조

**저장 위치**: `clusters.params_json->>'topic_category'`

**코드 위치**: `worker/pipeline/tfidf_clustering.py` 라인 434
```python
"topic_category": category,
```

### 검증 결과

⚠️ **현재 DB 상태**: 클러스터 데이터 없음

- 최신 run_id: 30 (cluster_tfidf, completed)
- 클러스터 수: 0개
- 메타데이터: `{"clusters_created": 0, "posts_processed": 3020}`

**가능한 원인**:
1. 클러스터링 실행 중 오류 발생 (하지만 status는 completed)
2. 데이터가 없어서 클러스터가 생성되지 않음
3. DB 저장 로직에 문제가 있을 수 있음

### 스키마 적합성

✅ **스키마는 적합함**
- `params_json`에 `topic_category` 저장 가능
- `cluster_assignments`를 통해 post-cluster 매핑 가능
- `cluster_id`로 클러스터 추적 가능

---

## [3] DB 데이터 분포 검증 (정량 체크)

### 현재 DB 상태

⚠️ **클러스터링 결과 없음**

- 전체 클러스터 수: 0
- topic_category별 클러스터 수: 모두 0
- 클러스터링된 포스트 수: 0

### Raw 데이터 상태

- `raw_reddit_posts` 수: 3020개
- 최신 pipeline run: run_id 30 (completed, 하지만 클러스터 0개)

---

## [4] 클러스터 결과 샘플 검증 (품질 체크)

⚠️ **샘플 검증 불가**: DB에 클러스터 데이터가 없음

---

## [5] 오류/위험 신호 체크

### 발견된 문제

1. ⚠️ **클러스터가 생성되지 않음**
   - run 30이 completed 상태이지만 클러스터 0개
   - 메타데이터: `clusters_created: 0`
   - 가능한 원인: 코드 실행 중 예외 발생 또는 데이터 필터링으로 인한 빈 결과

2. ⚠️ **코드 로직 확인 필요**
   - `worker/pipeline/tfidf_clustering.py` 라인 384-388에서 포스트가 0개인 경우 스킵
   - 하지만 3020개 포스트가 있는데 클러스터가 0개인 것은 이상함

### 코드 로직 재검토 필요 사항

**라인 384-388**: 포스트가 0개인 경우 스킵
```python
if len(posts) == 0:
    logger.warning(f"⚠️  {category}: 데이터 없음 (post 수: 0)")
    category_stats["status"] = "no_data"
    stats["categories"][category] = category_stats
    continue
```

**라인 396**: `cluster_posts_within_category()` 호출
- 이 함수가 빈 리스트를 반환할 가능성 확인 필요

**라인 401-405**: 클러스터 그룹 처리
```python
for cluster_idx, cluster_group in enumerate(cluster_groups):
    cluster_label, cluster_posts = list(cluster_group.items())[0]
    
    if len(cluster_posts) == 0:
        continue  # 빈 클러스터 스킵
```

---

## [6] 최종 판정

### 검증 결과 요약

| 항목 | 상태 | 비고 |
|------|------|------|
| 구조 적합성 | ✅ PASS | 코드 구조는 올바름 |
| DB 저장 상태 | ⚠️ PARTIAL | 스키마는 적합하나 데이터 없음 |
| 데이터 분포 | ❌ FAIL | 클러스터 데이터 없음 |
| 샘플 품질 | ❌ FAIL | 검증 불가 (데이터 없음) |
| 오류 체크 | ⚠️ WARNING | 클러스터가 생성되지 않음 |

### 최종 판정

- **구조 적합성**: ✅ **PASS**
  - 코드 구조는 topic_category별로 분리되어 실행되도록 올바르게 작성됨
  
- **DB 저장 상태**: ⚠️ **PARTIAL**
  - 스키마는 적합하나 실제 데이터가 저장되지 않음
  - `params_json`에 `topic_category` 저장 구조는 올바름

- **다음 단계(SERP 질문 생성)로 진행 가능 여부**: ❌ **NO**

### 수정 필요 사항

#### 1. 클러스터링 재실행 필요
- 현재 DB에 클러스터 데이터가 없음
- run 30이 completed이지만 클러스터가 생성되지 않은 원인 파악 필요

#### 2. 디버깅 포인트
- `worker/pipeline/tfidf_clustering.py` 라인 396: `cluster_posts_within_category()` 반환값 확인
- 로그 확인: 각 카테고리별 포스트 수와 클러스터 생성 여부
- 예외 처리: 클러스터링 실패 시 로그 및 에러 메시지 확인

#### 3. 코드 수정 제안 (필요시)

**라인 396 이후 디버깅 로그 추가**:
```python
cluster_groups = cluster_posts_within_category(posts, category)
logger.info(f"생성된 sub-cluster 수: {len(cluster_groups)}")

if len(cluster_groups) == 0:
    logger.warning(f"⚠️  {category}: 클러스터 그룹이 비어있음 (포스트 수: {len(posts)})")
    # 원인 파악을 위한 추가 로그
```

**라인 401-405 예외 처리 강화**:
```python
for cluster_idx, cluster_group in enumerate(cluster_groups):
    try:
        cluster_label, cluster_posts = list(cluster_group.items())[0]
        
        if len(cluster_posts) == 0:
            logger.warning(f"빈 클러스터 그룹 발견: {cluster_label}")
            continue
    except Exception as e:
        logger.error(f"클러스터 그룹 처리 중 오류: {e}, group={cluster_group}")
        continue
```

---

## 결론

**코드 구조는 올바르게 작성되어 있으며, topic_category별로 독립적으로 클러스터링이 수행되도록 설계되었습니다.**

하지만 **실제 DB에 클러스터 데이터가 저장되지 않았으므로**, 클러스터링을 재실행하여 데이터를 생성한 후 다시 검증해야 합니다.

재실행 후 검증 시 확인할 사항:
1. 각 topic_category별로 클러스터가 생성되었는지
2. `params_json`에 `topic_category`가 정확히 저장되었는지
3. 동일 post_id가 여러 topic_category에 중복 할당되지 않았는지
4. cluster_id가 각 카테고리 내에서만 의미를 갖는지
