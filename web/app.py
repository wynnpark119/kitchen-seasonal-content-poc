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
import os
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 명시적으로 로드 (OpenAI API 키 등)
env_path = project_root / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=True)
    except ImportError:
        # dotenv가 없으면 직접 읽기
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ[key] = value

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

# 탭 구성 (최종 스펙 기준)
tab1, tab2, tab3 = st.tabs([
    "🧠 Reddit 토픽 분석",
    "🔎 구글 AI 검색 결과 분석",
    "🏠 LG전자 HS 마스터 토픽 제안"
])

# ============================================================================
# TAB 1: Reddit 토픽 분석
# ============================================================================
with tab1:
    st.header("🧠 Reddit 토픽 분석")
    render_clustering_results()

# ============================================================================
# TAB 2: 구글 AI 검색 결과 분석
# ============================================================================
with tab2:
    st.header("🔎 구글 AI 검색 결과 분석")
    render_trend_explorer()

# ============================================================================
# TAB 3: LG전자 HS 마스터 토픽 제안
# ============================================================================
with tab3:
    st.header("🏠 LG전자 HS 마스터 토픽 제안")
    render_master_topics()
