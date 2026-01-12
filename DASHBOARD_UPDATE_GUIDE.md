# 대시보드 업데이트 가이드

## 변경 사항

### 기존 구조
- Post 단위 임베딩 기반 클러스터 표시
- 동적 클러스터 수

### 새로운 구조
- 4개 고정 클러스터 (카테고리별)
- 클러스터 요약 기반 표시
- SERP 결과 통합

## 대시보드에서 보여줘야 할 최소 구조

### 1. Topic(Cluster) 리스트 페이지

**표시 항목**:
- 주제명 (카테고리명)
- 대표 키워드 (Top 10)
- Reddit post 수
- SERP 결과 수
- 클러스터 요약 텍스트 (미리보기)

**쿼리 예시**:
```sql
SELECT 
    c.cluster_id,
    c.params_json->>'category' as category,
    c.size as reddit_post_count,
    (SELECT COUNT(*) FROM serp_results sr WHERE sr.cluster_id = c.cluster_id) as serp_result_count,
    c.params_json->>'summary' as summary,
    c.params_json->'top_keywords' as top_keywords
FROM clusters c
WHERE c.created_from_run_id = %s
AND c.noise_label = FALSE
ORDER BY c.cluster_id
```

### 2. Topic 상세 페이지

**표시 항목**:
- 주제명 및 전체 요약
- 대표 Reddit post (10개)
  - 제목, 본문 미리보기
  - Upvotes, Comments 수
  - Permalink 링크
- 대표 SERP 링크 (10개)
  - URL, Title, Snippet
  - Source (도메인)
  - Position (검색 순위)

**쿼리 예시**:
```sql
-- 대표 Reddit posts
SELECT 
    rp.reddit_post_id,
    rp.title,
    rp.body,
    rp.upvotes,
    rp.num_comments,
    rp.permalink
FROM cluster_assignments ca
JOIN raw_reddit_posts rp ON ca.doc_id = rp.reddit_post_id
WHERE ca.cluster_id = %s
AND ca.is_representative = TRUE
ORDER BY rp.upvotes DESC, rp.num_comments DESC
LIMIT 10

-- 대표 SERP 결과
SELECT 
    url,
    title,
    snippet,
    source,
    position
FROM serp_results
WHERE cluster_id = %s
ORDER BY position ASC
LIMIT 10
```

## 구현 예시

### Streamlit 페이지 구조

```python
# web/app.py에 추가할 섹션

def show_topic_list():
    """Topic 리스트 페이지"""
    st.header("Topics (Clusters)")
    
    # 클러스터 목록 조회
    clusters = get_clusters_with_stats()
    
    for cluster in clusters:
        with st.expander(f"{cluster['category']} ({cluster['reddit_post_count']} posts)"):
            st.write(f"**Summary**: {cluster['summary']}")
            st.write(f"**Top Keywords**: {', '.join(cluster['top_keywords'][:10])}")
            st.write(f"**SERP Results**: {cluster['serp_result_count']} results")
            
            if st.button(f"View Details", key=f"cluster_{cluster['cluster_id']}"):
                st.session_state['selected_cluster_id'] = cluster['cluster_id']
                st.rerun()

def show_topic_detail(cluster_id: int):
    """Topic 상세 페이지"""
    st.header("Topic Details")
    
    # 클러스터 정보
    cluster_info = get_cluster_info(cluster_id)
    st.write(f"**Category**: {cluster_info['category']}")
    st.write(f"**Summary**: {cluster_info['summary']}")
    
    # 대표 Reddit posts
    st.subheader("Representative Reddit Posts")
    posts = get_representative_posts(cluster_id)
    for post in posts:
        st.write(f"**{post['title']}**")
        st.write(f"Upvotes: {post['upvotes']}, Comments: {post['num_comments']}")
        st.write(f"[View on Reddit]({post['permalink']})")
        st.divider()
    
    # 대표 SERP 결과
    st.subheader("Top SERP Results")
    serp_results = get_top_serp_results(cluster_id)
    for result in serp_results:
        st.write(f"**{result['title']}**")
        st.write(f"{result['snippet']}")
        st.write(f"[{result['source']}]({result['url']}) - Position: {result['position']}")
        st.divider()
```

## 데이터베이스 쿼리 함수

`web/db_queries.py`에 추가할 함수들:

```python
def get_clusters_with_stats(run_id: int):
    """클러스터 목록과 통계 조회"""
    # 구현 필요

def get_cluster_info(cluster_id: int):
    """클러스터 상세 정보 조회"""
    # 구현 필요

def get_representative_posts(cluster_id: int, limit: int = 10):
    """대표 Reddit posts 조회"""
    # 구현 필요

def get_top_serp_results(cluster_id: int, limit: int = 10):
    """상위 SERP 결과 조회"""
    # 구현 필요
```
