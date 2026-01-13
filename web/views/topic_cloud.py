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


def create_interactive_keyword_viz(keywords_list: List[str] = None, keyword_freq: Dict[str, int] = None) -> None:
    """
    인터랙티브한 타원형 키워드 시각화 생성 및 표시
    
    Args:
        keywords_list: 키워드 리스트 (옵션, keyword_freq가 없을 때 사용)
        keyword_freq: 키워드 빈도 딕셔너리 (우선 사용)
    """
    try:
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
        
        # 상위 키워드만 선택 (너무 많으면 시각화가 복잡해짐)
        top_keywords = dict(sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:50])
        
        # 빈도 정규화 (0-1 범위)
        max_freq = max(top_keywords.values())
        min_freq = min(top_keywords.values())
        freq_range = max_freq - min_freq if max_freq != min_freq else 1
        
        # 타원형 레이아웃 생성 (극좌표 사용)
        keywords = list(top_keywords.keys())
        frequencies = list(top_keywords.values())
        
        # 각도 계산 (타원형 배치)
        n = len(keywords)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        
        # 반지름 계산 (빈도에 비례, 타원형으로 만들기 위해 x, y 축 비율 조정)
        normalized_freqs = [(f - min_freq) / freq_range for f in frequencies]
        
        # 타원형 좌표 생성 (x축을 더 길게)
        x_coords = []
        y_coords = []
        sizes = []
        texts = []
        
        for i, (angle, freq, keyword) in enumerate(zip(angles, frequencies, keywords)):
            # 타원형 배치 (x축: 1.5배, y축: 1배)
            radius = 0.3 + normalized_freqs[i] * 0.7  # 0.3 ~ 1.0 범위
            x = radius * 1.5 * np.cos(angle)
            y = radius * np.sin(angle)
            
            x_coords.append(x)
            y_coords.append(y)
            sizes.append(freq * 10 + 8)  # 최소 8, 최대 빈도에 따라 증가
            texts.append(keyword)
        
        # Plotly 인터랙티브 시각화 생성
        fig = go.Figure()
        
        # 키워드별로 scatter plot 추가
        for i, (x, y, size, text, freq) in enumerate(zip(x_coords, y_coords, sizes, texts, frequencies)):
            fig.add_trace(go.Scatter(
                x=[x],
                y=[y],
                mode='markers+text',
                marker=dict(
                    size=size,
                    color=freq,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="빈도"),
                    line=dict(width=1, color='rgba(255, 255, 255, 0.3)')
                ),
                text=text,
                textposition='middle center',
                textfont=dict(
                    size=max(10, min(16, size / 3)),
                    color='white'
                ),
                hovertemplate=f'<b>{text}</b><br>빈도: {freq}<extra></extra>',
                name=text
            ))
        
        # 레이아웃 설정
        fig.update_layout(
            title='',
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=[-1.2, 1.2]
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=[-1.2, 1.2],
                scaleanchor="x",
                scaleratio=0.67  # 타원형 비율 (y/x = 2/3)
            ),
            plot_bgcolor='#1e1e28',
            paper_bgcolor='#1e1e28',
            font=dict(color='white'),
            showlegend=False,
            height=700,
            margin=dict(l=0, r=0, t=0, b=0),
            hovermode='closest'
        )
        
        # Streamlit에 표시
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        
    except Exception as e:
        logger.error(f"인터랙티브 시각화 생성 오류: {e}")
        st.error(f"시각화 생성 중 오류가 발생했습니다: {e}")


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
        create_interactive_keyword_viz(keyword_freq=keyword_freq_from_json)
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
            
            # 전체 키워드로 인터랙티브 시각화 생성
            create_interactive_keyword_viz(all_keywords)
            
        except Exception as e:
            st.error(f"Error loading topic cloud data: {e}")
            st.info("Not available")
