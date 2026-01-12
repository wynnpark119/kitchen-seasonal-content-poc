"""
LG전자용 콘텐츠 인텔리전스 대시보드

최종 스펙 기준 대시보드
- Clustering Results
- Trend Explorer  
- Master Topics
"""
import streamlit as st
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
import sys
import os
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 콘솔 출력
    ]
)

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
# DATABASE_URL을 직접 환경 변수에서 읽기 (common.config 모듈 로딩 문제 방지)
DATABASE_URL = (
    os.getenv("DATABASE_URL") or 
    os.getenv("RAILWAY_DATABASE_URL") or
    os.getenv("POSTGRES_URL") or
    os.getenv("POSTGRES_PRIVATE_URL")
)

# common.openai_client는 별도로 import
from common.openai_client import is_openai_available, load_openai_api_key

# 디버깅: OpenAI API 키 상태 확인
print("=" * 60)
print("OpenAI API 키 상태 확인")
print("=" * 60)
if not is_openai_available():
    api_key = load_openai_api_key()
    if api_key:
        print(f"⚠️ API 키는 로드되었지만 is_openai_available()이 False를 반환합니다. 키 길이: {len(api_key)}")
    else:
        print("⚠️ OpenAI API 키가 로드되지 않았습니다.")
        env_key = os.getenv('OPENAI_API_KEY', 'NOT SET')
        if env_key != 'NOT SET':
            print(f"환경 변수 OPENAI_API_KEY: {env_key[:20]}... (길이: {len(env_key)})")
        else:
            print("환경 변수 OPENAI_API_KEY: NOT SET")
        print("💡 .env 파일 경로:", project_root / ".env")
else:
    api_key = load_openai_api_key()
    print(f"✅ OpenAI API 키가 정상적으로 로드되었습니다. (길이: {len(api_key) if api_key else 0})")
print("=" * 60)

# 뷰 임포트
from web.views.clustering_results import render_clustering_results
from web.views.trend_explorer import render_trend_explorer
from web.views.master_topics import render_master_topics
from web.views.reddit_collection_status import render_reddit_collection_status

# 페이지 설정
st.set_page_config(
    page_title="LG전자 HS 마스터 아티클 대시보드",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 사이드바: OpenAI API 키 입력 (환경변수가 없을 때만 표시)
if not is_openai_available():
    with st.sidebar:
        st.header("⚙️ 설정")
        st.markdown("### OpenAI API 키")
        st.markdown("환경변수에 API 키가 설정되지 않았습니다.")
        
        # 세션 상태에서 API 키 가져오기
        if 'openai_api_key_input' not in st.session_state:
            st.session_state.openai_api_key_input = ""
        
        api_key_input = st.text_input(
            "OpenAI API Key",
            value=st.session_state.openai_api_key_input,
            type="password",
            help="환경변수 OPENAI_API_KEY가 없을 때만 사용됩니다.",
            key="openai_api_key_sidebar_input"
        )
        
        if api_key_input and api_key_input != st.session_state.openai_api_key_input:
            # 새 키가 입력되었으면 환경변수에 설정
            os.environ["OPENAI_API_KEY"] = api_key_input
            st.session_state.openai_api_key_input = api_key_input
            # 클라이언트 리셋 (다음 호출 시 새 키 사용)
            from common.openai_client import reset_client
            reset_client()
            st.success("✅ API 키가 설정되었습니다. 페이지를 새로고침해주세요.")
        
        if st.session_state.openai_api_key_input:
            st.info("💡 API 키가 입력되었습니다. 인사이트 생성 기능을 사용할 수 있습니다.")

# 헤더
st.title("🏠 LG전자 HS 마스터 아티클 대시보드")
st.markdown("---")

# 탭 구성 (최종 스펙 기준)
tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 LG전자 HS 마스터 토픽 제안",
    "🧠 Reddit 토픽 분석",
    "🔎 구글 AI 검색 결과 분석",
    "📊 레딧 수집 및 분석 현황"
])

# ============================================================================
# TAB 1: LG전자 HS 마스터 토픽 제안
# ============================================================================
with tab1:
    st.header("🏠 LG전자 HS 마스터 토픽 제안")
    st.caption("앞선 분석을 종합해, LG전자 HS 관점에서 활용 가능한 마스터 토픽을 제안합니다. 고객의 생활 변화 흐름을 반영해, 시즌별 콘텐츠와 커뮤니케이션 전략으로 확장 가능한 주제를 도출합니다.")
    st.markdown("---")
    render_master_topics()

# ============================================================================
# TAB 2: Reddit 토픽 분석
# ============================================================================
with tab2:
    st.header("🧠 Reddit 토픽 분석")
    st.caption("고객이 일상 속에서 실제로 해결하려는 문제와 관심사를 AI로 분석해, 라이프 콘텍스트 기반의 주제를 도출합니다.")
    st.markdown("---")
    render_clustering_results()

# ============================================================================
# TAB 3: 구글 AI 검색 결과 분석
# ============================================================================
with tab3:
    st.header("🔎 구글 AI 검색 결과 분석")
    st.caption("구글 AI Overview에 참고되는 질문·주제 구조인지 여부를 검증해, 콘텐츠 확장 가능성을 판단합니다.")
    st.markdown("**구글 AI 검색 결과 분석에 사용된 탐색 키워드는 Reddit에서 나타난 실제 문제 인식 문장과 검색 단계에서 자주 함께 등장하는 연관 질의를 AI로 결합·정제한 뒤, GPT를 통해 질문 구조와 탐색 맥락을 확장·보완하여 생성되었습니다.**")
    st.markdown("---")
    render_trend_explorer()

# ============================================================================
# TAB 4: 레딧 수집 및 분석 현황
# ============================================================================
with tab4:
    st.header("📊 레딧 수집 및 분석 현황")
    render_reddit_collection_status()
