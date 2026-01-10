"""
레딧 수집 및 분석 현황 뷰

카테고리별 통계 오버뷰 표시
"""
import streamlit as st
import pandas as pd
import importlib
import sys

# 모듈 재로드를 위해 import
from services import clustering_service

# Streamlit 모듈 캐싱 문제 해결: 모듈 재로드
if 'services.clustering_service' in sys.modules:
    importlib.reload(clustering_service)


def render_reddit_collection_status():
    """레딧 수집 및 분석 현황 탭 렌더링"""
    clustering_service_instance = clustering_service.get_clustering_service()
    
    try:
        # 카테고리별 오버뷰 조회
        overview_df = clustering_service_instance.get_category_overview()
        
        if len(overview_df) == 0:
            st.warning("⚠️ 레딧 수집 데이터가 없습니다.")
            st.info("데이터 수집이 완료되면 결과가 표시됩니다.")
            return
        
        st.markdown("### 📊 카테고리별 통계")
        
        # 전체 통계
        total_posts = overview_df['posts'].sum()
        total_comments = overview_df['comments'].sum()
        total_clusters = overview_df['clusters'].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("전체 클러스터", f"{total_clusters}개")
        with col2:
            st.metric("전체 포스트", f"{total_posts}개")
        with col3:
            st.metric("전체 코멘트", f"{total_comments:,}개")
        with col4:
            avg_comments = total_comments / total_posts if total_posts > 0 else 0
            st.metric("평균 코멘트/포스트", f"{avg_comments:.1f}개")
        
        st.markdown("---")
        
        # 카테고리별 상세 통계
        st.markdown("#### 카테고리별 상세")
        category_cols = st.columns(len(overview_df))
        
        for idx, (_, row) in enumerate(overview_df.iterrows()):
            with category_cols[idx]:
                category_name = row['category']
                # 카테고리 이름을 더 읽기 쉽게 표시
                display_name = category_name.replace('_', ' ').title()
                
                st.markdown(f"**{display_name}**")
                st.metric("클러스터", f"{int(row['clusters'])}개", delta=None)
                st.metric("포스트", f"{int(row['posts'])}개", delta=None)
                st.metric("코멘트", f"{int(row['comments']):,}개", delta=None)
        
    except Exception as e:
        st.error(f"Error loading reddit collection status: {e}")
        import traceback
        st.code(traceback.format_exc())
