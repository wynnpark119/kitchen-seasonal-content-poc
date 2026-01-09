"""
Clustering Results 뷰

클러스터링 결과 표시
"""
import streamlit as st
import pandas as pd
from typing import Optional

from services.clustering_service import get_clustering_service
from services.gpt_service import get_gpt_service
from common.openai_client import is_openai_available


def render_clustering_results():
    """Reddit 토픽 분석 탭 렌더링"""
    clustering_service = get_clustering_service()
    gpt_service = get_gpt_service()
    
    try:
        clusters_df = clustering_service.get_all_clusters()
        
        if len(clusters_df) == 0:
            st.warning("⚠️ Reddit 토픽 분석 데이터가 없습니다.")
            st.info("클러스터링이 완료되면 결과가 표시됩니다.")
            return
        
        # 카테고리 필터
        categories = clusters_df['topic_category'].dropna().unique()
        available_categories = sorted([cat for cat in categories if pd.notna(cat)])
        
        if available_categories:
            selected_category = st.selectbox(
                "카테고리 선택",
                ["All"] + available_categories,
                key="cluster_category_filter"
            )
            
            # 필터링
            if selected_category == "All":
                filtered_df = clusters_df[clusters_df['topic_category'].notna()]
            else:
                filtered_df = clusters_df[clusters_df['topic_category'] == selected_category]
            
            # 클러스터 표시
            for idx, (_, cluster_row) in enumerate(filtered_df.iterrows()):
                cluster_id = cluster_row['cluster_id']
                cluster_id_str = str(cluster_id)
                cluster_name = cluster_row.get('cluster_name', f"Cluster_{cluster_id}")
                topic_category = cluster_row.get('topic_category')
                
                if pd.isna(topic_category) or topic_category is None:
                    topic_category_display = 'Unknown'
                else:
                    topic_category_display = topic_category
                
                size = cluster_row.get('size', 0)
                sub_cluster_index = cluster_row.get('sub_cluster_index')
                top_keywords = cluster_row.get('top_keywords', [])
                if not isinstance(top_keywords, list):
                    top_keywords = []
                
                with st.expander(f"📌 {cluster_name} ({topic_category_display})"):
                    # 기본 정보
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Cluster ID", cluster_id_str)
                    with col2:
                        st.metric("Size", int(size))
                    with col3:
                        st.metric("Sub Cluster Index", sub_cluster_index if pd.notna(sub_cluster_index) else "N/A")
                    with col4:
                        st.metric("Representative", int(cluster_row.get('representative_count', 0)))
                    
                    # 요약 표시
                    summary = cluster_row.get('summary')
                    if pd.notna(summary) and summary:
                        st.markdown("**📝 요약:**")
                        st.info(summary)
                    
                    # GPT 요약 (선택적, 실패해도 화면 깨지지 않음)
                    try:
                        if is_openai_available():
                            with st.spinner("GPT로 클러스터 요약 생성 중..."):
                                gpt_summary = gpt_service.generate_cluster_summary(
                                    cluster_id_str,
                                    top_keywords[:10] if top_keywords else [],
                                    int(size),
                                    topic_category_display if topic_category_display != 'Unknown' else 'Unknown'
                                )
                                if gpt_summary:
                                    st.markdown("**📝 요약 (GPT 생성):**")
                                    st.info(gpt_summary)
                    except Exception as gpt_error:
                        # GPT 실패해도 계속 진행
                        pass
                    
                    # Top Keywords
                    if top_keywords:
                        st.markdown("**🔑 주요 키워드:**")
                        keywords_str = ", ".join(top_keywords[:20])
                        st.write(keywords_str)
                        if len(top_keywords) > 20:
                            st.caption(f"총 {len(top_keywords)}개 키워드 중 상위 20개 표시")
                    
                    # 대표 포스트
                    try:
                        representative_posts = clustering_service.get_representative_posts(cluster_id, limit=5)
                        
                        if len(representative_posts) > 0:
                            st.markdown("**📌 대표 포스트:**")
                            for post_idx, (_, post_row) in enumerate(representative_posts.iterrows()):
                                with st.expander(f"Post {post_idx + 1}: {post_row.get('title', 'N/A')[:50]}..."):
                                    st.write(f"**Title**: {post_row.get('title', 'N/A')}")
                                    st.write(f"**Upvotes**: {post_row.get('upvotes', 0)}")
                                    st.write(f"**Comments**: {post_row.get('num_comments', 0)}")
                                    if post_row.get('permalink'):
                                        st.write(f"**Link**: https://reddit.com{post_row.get('permalink', '')}")
                    except Exception as e:
                        # 대표 포스트 조회 실패해도 계속 진행
                        pass
        else:
            st.info("Not available")
            
    except Exception as e:
        st.error(f"Error loading clustering results: {e}")
        st.info("Not available")


