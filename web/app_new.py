"""
LG전자용 콘텐츠 인텔리전스 대시보드

최종 스펙 기준 대시보드
- Clustering Results
- Trend Explorer  
- Master Topics
"""
import streamlit as st
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
from common.config import DATABASE_URL
from common.openai_client import is_openai_available

# 뷰 임포트
from web.views.clustering_results import render_clustering_results
from web.views.trend_explorer import render_trend_explorer
from web.views.master_topics import render_master_topics

# 페이지 설정
st.set_page_config(
    page_title="LG전자 HS 마스터 아티클 대시보드",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 헤더
st.title("🏠 LG전자 HS 마스터 아티클 대시보드")
st.markdown("---")

# 탭 구성 (Overview 제거, 3개 탭만)
tab1, tab2, tab3 = st.tabs([
    "🎯 Clustering Results",
    "📈 Trend Explorer",
    "🎯 Master Topics"
])

# ============================================================================
# TAB 1: Clustering Results
# ============================================================================
with tab1:
    render_clustering_results()

# ============================================================================
# TAB 2: Trend Explorer
# ============================================================================
with tab2:
    render_trend_explorer()

# ============================================================================
# TAB 3: Master Topics
# ============================================================================
with tab3:
    render_master_topics()
