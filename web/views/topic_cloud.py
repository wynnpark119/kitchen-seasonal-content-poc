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
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# 모듈 재로드를 위해 import
from services import clustering_service
from common.path_utils import get_data_dir

# 로거 설정
logger = logging.getLogger(__name__)

# Streamlit 모듈 캐싱 문제 해결: 모듈 재로드
if 'services.clustering_service' in sys.modules:
    importlib.reload(clustering_service)


def load_keyword_frequencies_from_json() -> Dict[str, int]:
    """
    JSON 파일에서 키워드 빈도 데이터 로드
    
    Returns:
        Dict[str, int]: 키워드별 빈도 딕셔너리
    """
    try:
        data_dir = get_data_dir()
        json_path = data_dir / "topic_cloud_keywords.json"
        
        if not json_path.exists():
            logger.warning(f"키워드 JSON 파일을 찾을 수 없습니다: {json_path}")
            return {}
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # adjusted_keyword_frequencies와 downweighted_terms를 합침
        keyword_freq = {}
        
        if 'adjusted_keyword_frequencies' in data:
            keyword_freq.update(data['adjusted_keyword_frequencies'])
        
        if 'downweighted_terms' in data:
            keyword_freq.update(data['downweighted_terms'])
        
        return keyword_freq
        
    except Exception as e:
        logger.error(f"키워드 JSON 파일 로드 오류: {e}")
        return {}


def create_wordcloud(keywords_list: List[str] = None, keyword_freq: Dict[str, int] = None, title: str = "Topic Cloud") -> None:
    """
    타원형 마스크를 사용한 인터랙티브 워드 클라우드 생성 및 표시
    
    Args:
        keywords_list: 키워드 리스트 (옵션, keyword_freq가 없을 때 사용)
        keyword_freq: 키워드 빈도 딕셔너리 (우선 사용)
        title: 워드 클라우드 제목
    """
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        from PIL import Image
        import io
        
        # keyword_freq가 제공되지 않으면 keywords_list에서 계산
        if keyword_freq is None:
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
            
            # lemon 키워드의 빈도를 asparagus와 동일하게 설정
            asparagus_freq = 0
            lemon_freq = 0
            
            # asparagus 빈도 찾기 (대소문자 구분 없이)
            for kw, freq in keyword_freq.items():
                if kw.lower() == 'asparagus':
                    asparagus_freq = freq
                elif kw.lower() == 'lemon':
                    lemon_freq = freq
            
            # asparagus가 있고 lemon이 있으면 lemon의 빈도를 asparagus와 동일하게 설정
            if asparagus_freq > 0:
                if lemon_freq > 0:
                    keyword_freq['lemon'] = asparagus_freq
                else:
                    keyword_freq['lemon'] = asparagus_freq
        
        if not keyword_freq:
            st.info("키워드 빈도 데이터가 없습니다.")
            return
        
        # 타원형 마스크 생성
        width, height = 1200, 600
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # 타원형 마스크 그리기 (중앙에 타원)
        center_x, center_y = width // 2, height // 2
        ellipse_width = width * 0.85  # 타원 너비
        ellipse_height = height * 0.75  # 타원 높이
        
        y, x = np.ogrid[:height, :width]
        mask = ((x - center_x) / (ellipse_width / 2))**2 + ((y - center_y) / (ellipse_height / 2))**2 <= 1
        mask = (~mask).astype(np.uint8) * 255
        
        # 워드 클라우드 생성 (타원형 마스크 사용)
        wordcloud = WordCloud(
            width=width,
            height=height,
            background_color='#1e1e28',  # 다크 모드 배경
            colormap='viridis',  # 다크 모드에 잘 보이는 색상 맵
            max_words=200,
            relative_scaling=0.5,
            collocations=False,
            font_path=None,  # 시스템 기본 폰트 사용
            prefer_horizontal=0.7,
            min_font_size=10,
            max_font_size=120,
            random_state=42,  # 고정된 랜덤 시드로 매번 동일한 배치
            mask=mask,  # 타원형 마스크 적용
            contour_width=0,
            contour_color='#1e1e28'
        ).generate_from_frequencies(keyword_freq)
        
        # matplotlib로 이미지 생성
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        
        # 다크 모드 스타일 적용
        fig.patch.set_facecolor('#1e1e28')
        ax.set_facecolor('#1e1e28')
        
        # Streamlit에 표시
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        
    except ImportError as e:
        st.error("⚠️ 워드 클라우드 라이브러리가 설치되지 않았습니다.")
        st.info("**로컬 개발 환경에서 설치:**")
        st.code("pip install wordcloud matplotlib pillow", language="bash")
        st.info("**또는:**")
        st.code("python3 -m pip install wordcloud matplotlib pillow", language="bash")
        st.warning("Railway 배포 환경에서는 requirements.txt를 통해 자동으로 설치됩니다.")
        logger.error(f"Import error: {e}")
    except Exception as e:
        logger.error(f"워드 클라우드 생성 오류: {e}")
        st.error(f"워드 클라우드 생성 중 오류가 발생했습니다: {e}")


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
    # JSON 파일에서 키워드 빈도 로드 시도
    keyword_freq_from_json = load_keyword_frequencies_from_json()
    
    if keyword_freq_from_json:
        # JSON 파일에서 로드한 데이터 사용
        create_wordcloud(keyword_freq=keyword_freq_from_json)
    else:
        # 기존 방식: DB에서 데이터 로드
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
            st.info("Not available")
