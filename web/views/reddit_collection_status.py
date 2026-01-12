"""
레딧 수집 및 분석 현황 뷰

주제별 포스트 통계 표시
"""
import streamlit as st
import pandas as pd
import importlib
import sys
from datetime import datetime

# 모듈 재로드를 위해 import
from services import clustering_service

# Streamlit 모듈 캐싱 문제 해결: 모듈 재로드
if 'services.clustering_service' in sys.modules:
    importlib.reload(clustering_service)


def render_reddit_collection_status():
    """레딧 수집 및 분석 현황 탭 렌더링"""
    clustering_service_instance = clustering_service.get_clustering_service()
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # 전체 클러스터 조회
        try:
            logger.info("Calling get_all_clusters...")
            clusters_df = clustering_service_instance.get_all_clusters()
            logger.info(f"get_all_clusters returned {len(clusters_df)} clusters")
            
        except AttributeError as e:
            st.warning("⚠️ 클러스터 데이터를 불러올 수 없습니다.")
            st.info("데이터 수집이 완료되면 결과가 표시됩니다.")
            logger.warning(f"get_all_clusters method not found: {e}")
            import traceback
            with st.expander("🔍 상세 오류 보기"):
                st.code(traceback.format_exc())
            return
        except Exception as e:
            st.warning("⚠️ 데이터를 불러오는 중 오류가 발생했습니다.")
            st.info("데이터 수집이 완료되면 결과가 표시됩니다.")
            logger.exception("Error calling get_all_clusters")
            import traceback
            with st.expander("🔍 상세 오류 보기"):
                st.code(traceback.format_exc())
            return
        
        if len(clusters_df) == 0:
            st.warning("⚠️ 레딧 수집 데이터가 없습니다.")
            st.info("💡 데이터 수집이 완료되지 않았거나, 데이터베이스에 클러스터링 결과가 없습니다.")
            logger.warning("get_all_clusters returned empty DataFrame")
            return
        
        # 전체 통계
        total_posts = clusters_df['size'].sum() if 'size' in clusters_df.columns else 0
        
        st.markdown("### 📊 전체 통계")
        st.metric("전체 포스트", f"{total_posts}개")
        
        # 최종 수집 업데이트일
        today = datetime.now().strftime("%Y년 %m월 %d일")
        st.caption(f"최종 수집 업데이트일: {today}")
        
        st.markdown("---")
        
        # 주제별 포스트 개수
        st.markdown("### 📋 주제별 수집 현황")
        
        if 'topic_category' in clusters_df.columns:
            # 카테고리별로 그룹화하여 포스트 개수 집계
            category_stats = clusters_df.groupby('topic_category')['size'].sum().reset_index()
            category_stats.columns = ['category', 'posts']
            category_stats = category_stats.sort_values('category')
            
            for _, row in category_stats.iterrows():
                category = row['category']
                post_count = int(row['posts'])
                display_name = category.replace('_', ' ').title()
                
                st.markdown(f"**{display_name}**: {post_count}개")
        else:
            st.info("주제별 정보가 없습니다.")
        
    except Exception as e:
        st.error(f"Error loading reddit collection status: {e}")
        import traceback
        st.code(traceback.format_exc())
