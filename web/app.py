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

# .env 파일 명시적으로 로드 (로컬 개발용, Railway에서는 환경 변수 사용)
env_path = project_root / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=False)  # override=False: 환경 변수가 우선
    except ImportError:
        # dotenv가 없으면 직접 읽기
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # 환경 변수가 이미 설정되어 있지 않을 때만 설정
                    if key and value and not os.getenv(key):
                        os.environ[key] = value

# 환경 변수 로드
from common.config import DATABASE_URL
from common.openai_client import is_openai_available, load_openai_api_key

# 디버깅: OpenAI API 키 상태 확인
if not is_openai_available():
    api_key = load_openai_api_key()
    if api_key:
        print(f"⚠️ API 키는 로드되었지만 is_openai_available()이 False를 반환합니다. 키 길이: {len(api_key)}")
    else:
        print("⚠️ OpenAI API 키가 로드되지 않았습니다.")
        print(f"환경 변수 OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'NOT SET')[:20]}...")
else:
    print("✅ OpenAI API 키가 정상적으로 로드되었습니다.")

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
