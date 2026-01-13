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
        
        # 제외할 키워드 목록
        excluded_keywords = {'produce'}
        
        # 제외할 키워드 필터링 (대소문자 구분 없이)
        filtered_keywords = [
            kw for kw in keywords_list 
            if kw.lower() not in excluded_keywords
        ]
        
        if not filtered_keywords:
            st.info("필터링 후 키워드가 없습니다.")
            return
        
        # 키워드 빈도 계산
        keyword_freq = Counter(filtered_keywords)
        
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
        # 제목 제거
        
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
        st.info("**로컬 개발 환경에서 설치:**")
        st.code("pip install wordcloud matplotlib", language="bash")
        st.info("**또는:**")
        st.code("python3 -m pip install wordcloud matplotlib", language="bash")
        st.warning("Railway 배포 환경에서는 requirements.txt를 통해 자동으로 설치됩니다.")
        logger.error(f"Import error: {e}")
        import traceback
        with st.expander("상세 오류 보기"):
            st.code(traceback.format_exc())
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
        
        # 전체 키워드로 워드 클라우드 생성
        create_wordcloud(all_keywords)
            
    except Exception as e:
        st.error(f"Error loading topic cloud data: {e}")
        import traceback
        with st.expander("상세 오류 보기"):
            st.code(traceback.format_exc())
        st.info("Not available")
