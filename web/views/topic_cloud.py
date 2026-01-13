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


def create_wordcloud_for_category(keywords_list: List[str], category_name: str) -> None:
    """
    카테고리별 워드 클라우드 생성 및 표시
    
    Args:
        keywords_list: 키워드 리스트
        category_name: 카테고리 이름
    """
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        import io
        
        if not keywords_list:
            st.info(f"{category_name} 카테고리에 키워드가 없습니다.")
            return
        
        # 키워드 빈도 계산
        keyword_freq = Counter(keywords_list)
        
        # 워드 클라우드 생성
        wordcloud = WordCloud(
            width=1200,
            height=600,
            background_color='#1e1e28',  # 다크 모드 배경
            colormap='viridis',  # 다크 모드에 잘 보이는 색상 맵
            max_words=150,
            relative_scaling=0.5,
            collocations=False,
            font_path=None,  # 시스템 기본 폰트 사용
            prefer_horizontal=0.7,
            min_font_size=10,
            max_font_size=100
        ).generate_from_frequencies(keyword_freq)
        
        # matplotlib로 이미지 생성
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title(category_name, fontsize=18, color='#ffffff', pad=20, fontweight='bold')
        
        # 다크 모드 스타일 적용
        fig.patch.set_facecolor('#1e1e28')
        ax.set_facecolor('#1e1e28')
        
        # Streamlit에 표시
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        
        # 키워드 통계 표시
        with st.expander(f"📊 {category_name} 키워드 통계"):
            top_keywords = keyword_freq.most_common(20)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**상위 키워드 (빈도순)**")
                for keyword, count in top_keywords[:10]:
                    st.caption(f"• {keyword}: {count}회")
            
            with col2:
                st.markdown("**상위 키워드 (계속)**")
                for keyword, count in top_keywords[10:]:
                    st.caption(f"• {keyword}: {count}회")
            
            st.caption(f"총 고유 키워드 수: {len(keyword_freq)}개")
            st.caption(f"총 키워드 사용 횟수: {sum(keyword_freq.values())}회")
        
    except ImportError:
        st.error("⚠️ 워드 클라우드 라이브러리가 설치되지 않았습니다.")
        st.info("다음 명령어로 설치하세요: `pip install wordcloud matplotlib`")
    except Exception as e:
        logger.error(f"워드 클라우드 생성 오류: {e}")
        st.error(f"워드 클라우드 생성 중 오류가 발생했습니다: {e}")
        import traceback
        with st.expander("상세 오류 보기"):
            st.code(traceback.format_exc())


def collect_keywords_by_category(clusters_df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    카테고리별로 키워드 수집
    
    Args:
        clusters_df: 클러스터 데이터프레임
        
    Returns:
        Dict[str, List[str]]: 카테고리별 키워드 리스트
    """
    category_keywords = {}
    
    for _, row in clusters_df.iterrows():
        topic_category = row.get('topic_category')
        
        if pd.isna(topic_category) or topic_category is None:
            continue
        
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
        
        # 카테고리별로 키워드 수집
        if topic_category not in category_keywords:
            category_keywords[topic_category] = []
        
        category_keywords[topic_category].extend(top_keywords)
    
    return category_keywords


def render_topic_cloud():
    """Topic Cloud 탭 렌더링"""
    clustering_service_instance = clustering_service.get_clustering_service()
    
    try:
        clusters_df = clustering_service_instance.get_all_clusters()
        
        if len(clusters_df) == 0:
            st.warning("⚠️ Reddit 토픽 분석 데이터가 없습니다.")
            st.info("클러스터링이 완료되면 결과가 표시됩니다.")
            return
        
        # 카테고리별로 키워드 수집
        category_keywords = collect_keywords_by_category(clusters_df)
        
        if not category_keywords:
            st.info("카테고리별 키워드 데이터가 없습니다.")
            return
        
        # 카테고리 라벨 매핑
        category_labels = {
            "SPRING_RECIPES": "Spring Recipes",
            "SPRING_KITCHEN_STYLING": "Spring Kitchen Styling",
            "REFRIGERATOR_ORGANIZATION": "Refrigerator Organization",
            "VEGETABLE_PREP_HANDLING": "Vegetable Prep & Handling"
        }
        
        # 카테고리 선택 드롭다운
        available_categories = sorted(category_keywords.keys())
        category_options = [category_labels.get(cat, cat.replace("_", " ").title()) for cat in available_categories]
        
        st.markdown("### 주제별 워드 클라우드")
        st.caption("각 주제의 주요 키워드를 시각화합니다.")
        
        # 카테고리 선택
        selected_category_label = st.selectbox(
            "주제 선택",
            category_options,
            key="topic_cloud_category"
        )
        
        # 선택된 라벨에 해당하는 카테고리 찾기
        selected_category = None
        for cat, label in category_labels.items():
            if label == selected_category_label:
                selected_category = cat
                break
        
        if selected_category is None:
            selected_category = available_categories[0]
        
        # 선택된 카테고리의 키워드로 워드 클라우드 생성
        if selected_category in category_keywords:
            keywords = category_keywords[selected_category]
            create_wordcloud_for_category(keywords, selected_category_label)
        else:
            st.warning(f"{selected_category_label} 카테고리에 키워드가 없습니다.")
        
        st.markdown("---")
        
        # 전체 카테고리 요약
        with st.expander("📈 전체 주제 요약"):
            summary_cols = st.columns(len(available_categories))
            
            for idx, category in enumerate(available_categories):
                with summary_cols[idx]:
                    keywords = category_keywords[category]
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
