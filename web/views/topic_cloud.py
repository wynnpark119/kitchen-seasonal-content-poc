"""
Topic Cloud 뷰

주제별 워드 클라우드 생성 및 표시
"""
import streamlit as st
import pandas as pd
import importlib
import sys
import logging
from collections import Counter
from typing import Dict, List
import json

# 모듈 재로드를 위해 import
from services import clustering_service

# 로거 설정
logger = logging.getLogger(__name__)

# Streamlit 모듈 캐싱 문제 해결: 모듈 재로드
if 'services.clustering_service' in sys.modules:
    importlib.reload(clustering_service)


def create_wordcloud(keywords_list: List[str], title: str = "Topic Cloud") -> None:
    """
    전체 키워드로 워드 클라우드 생성 및 표시
    
    Args:
        keywords_list: 키워드 리스트
        title: 워드 클라우드 제목
    """
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        import io
        
        if not keywords_list:
            st.info("키워드가 없습니다.")
            return
        
        # 키워드 빈도 계산
        keyword_freq = Counter(keywords_list)
        
        # 워드 클라우드 생성
        wordcloud = WordCloud(
            width=1200,
            height=600,
            background_color='#1e1e28',  # 다크 모드 배경
            colormap='viridis',  # 다크 모드에 잘 보이는 색상 맵
            max_words=200,
            relative_scaling=0.5,
            collocations=False,
            font_path=None,  # 시스템 기본 폰트 사용
            prefer_horizontal=0.7,
            min_font_size=10,
            max_font_size=120
        ).generate_from_frequencies(keyword_freq)
        
        # matplotlib로 이미지 생성
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title(title, fontsize=18, color='#ffffff', pad=20, fontweight='bold')
        
        # 다크 모드 스타일 적용
        fig.patch.set_facecolor('#1e1e28')
        ax.set_facecolor('#1e1e28')
        
        # Streamlit에 표시
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        
        # 키워드 통계 표시
        with st.expander("📊 키워드 통계"):
            top_keywords = keyword_freq.most_common(30)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**상위 키워드 (빈도순)**")
                for keyword, count in top_keywords[:10]:
                    st.caption(f"• {keyword}: {count}회")
            
            with col2:
                st.markdown("**상위 키워드 (계속)**")
                for keyword, count in top_keywords[10:20]:
                    st.caption(f"• {keyword}: {count}회")
            
            with col3:
                st.markdown("**상위 키워드 (계속)**")
                for keyword, count in top_keywords[20:]:
                    st.caption(f"• {keyword}: {count}회")
            
            st.caption(f"총 고유 키워드 수: {len(keyword_freq)}개")
            st.caption(f"총 키워드 사용 횟수: {sum(keyword_freq.values())}회")
        
    except ImportError as e:
        st.error("⚠️ 워드 클라우드 라이브러리가 설치되지 않았습니다.")
        st.info("라이브러리 설치 중입니다. 잠시 후 새로고침해주세요.")
        logger.error(f"Import error: {e}")
    except Exception as e:
        logger.error(f"워드 클라우드 생성 오류: {e}")
        st.error(f"워드 클라우드 생성 중 오류가 발생했습니다: {e}")
        import traceback
        with st.expander("상세 오류 보기"):
            st.code(traceback.format_exc())


def collect_all_keywords(clusters_df: pd.DataFrame) -> List[str]:
    """
    모든 클러스터의 키워드를 수집하여 하나의 리스트로 반환
    
    Args:
        clusters_df: 클러스터 데이터프레임
        
    Returns:
        List[str]: 모든 키워드 리스트
    """
    all_keywords = []
    
    for _, row in clusters_df.iterrows():
        # top_keywords 필드에서 키워드 추출
        top_keywords = row.get('top_keywords', [])
        
        if not top_keywords:
            continue
        
        # JSON 문자열인 경우 파싱
        if isinstance(top_keywords, str):
            try:
                top_keywords = json.loads(top_keywords)
            except:
                continue
        
        # 리스트가 아닌 경우 스킵
        if not isinstance(top_keywords, list):
            continue
        
        # 모든 키워드 수집
        all_keywords.extend(top_keywords)
    
    return all_keywords


def render_topic_cloud():
    """Topic Cloud 탭 렌더링"""
    clustering_service_instance = clustering_service.get_clustering_service()
    
    try:
        clusters_df = clustering_service_instance.get_all_clusters()
        
        if len(clusters_df) == 0:
            st.warning("⚠️ Reddit 토픽 분석 데이터가 없습니다.")
            st.info("클러스터링이 완료되면 결과가 표시됩니다.")
            return
        
        # 모든 키워드 수집
        all_keywords = collect_all_keywords(clusters_df)
        
        if not all_keywords:
            st.info("키워드 데이터가 없습니다.")
            return
        
        st.markdown("### 전체 키워드 워드 클라우드")
        st.caption("모든 주제의 키워드를 통합하여 시각화합니다.")
        
        # 전체 키워드로 워드 클라우드 생성
        create_wordcloud(all_keywords, "Reddit Topic Cloud - All Keywords")
        
        st.markdown("---")
        
        # 카테고리별 통계
        category_labels = {
            "SPRING_RECIPES": "Spring Recipes",
            "SPRING_KITCHEN_STYLING": "Spring Kitchen Styling",
            "REFRIGERATOR_ORGANIZATION": "Refrigerator Organization",
            "VEGETABLE_PREP_HANDLING": "Vegetable Prep & Handling"
        }
        
        # 카테고리별 키워드 수집 (통계용)
        category_keywords = {}
        for _, row in clusters_df.iterrows():
            topic_category = row.get('topic_category')
            if pd.isna(topic_category) or topic_category is None:
                continue
            
            top_keywords = row.get('top_keywords', [])
            if not top_keywords:
                continue
            
            if isinstance(top_keywords, str):
                try:
                    top_keywords = json.loads(top_keywords)
                except:
                    continue
            
            if not isinstance(top_keywords, list):
                continue
            
            if topic_category not in category_keywords:
                category_keywords[topic_category] = []
            category_keywords[topic_category].extend(top_keywords)
        
        # 카테고리별 통계 표시
        if category_keywords:
            with st.expander("📈 주제별 키워드 통계"):
                summary_cols = st.columns(len(category_keywords))
                
                for idx, (category, keywords) in enumerate(sorted(category_keywords.items())):
                    with summary_cols[idx]:
                        keyword_freq = Counter(keywords)
                        category_label = category_labels.get(category, category.replace("_", " ").title())
                        
                        st.metric(
                            label=category_label,
                            value=f"{len(keyword_freq)}개",
                            help=f"고유 키워드 수: {len(keyword_freq)}개\n총 사용 횟수: {sum(keyword_freq.values())}회"
                        )
            
    except Exception as e:
        st.error(f"Error loading topic cloud data: {e}")
        import traceback
        with st.expander("상세 오류 보기"):
            st.code(traceback.format_exc())
        st.info("Not available")
