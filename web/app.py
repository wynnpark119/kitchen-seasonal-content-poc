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
from web.views.keyword_msv_stats import render_keyword_msv_stats
from web.views.reddit_collection_posts import render_reddit_collection_posts
from web.views.overview import render_overview
from web.views.topic_cloud import render_topic_cloud

# 페이지 설정
st.set_page_config(
    page_title="LG전자 HS 마스터 아티클 대시보드",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 좌측 Sidebar 구성
# ============================================================================
with st.sidebar:
    # 대시보드 제목
    st.markdown(
        """
        <div style="margin-bottom: 8px;">
            <h2 style="font-size: 1.2em; margin-bottom: 0; margin-top: 0; color: #ffffff; font-weight: 600; line-height: 1.3; text-align: left;">
                LG Electronics<br>
                HS Master Article<br>
                Dashboard
            </h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 세션 상태 초기화
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "overview"
    
    # 페이지 옵션 정의 (불릿으로 통일)
    page_options = [
        ("overview", "• Overview"),
        ("exploration_status", "• 구글 검색 결과 현황"),
        ("reddit_collection_posts", "• 레딧 게시물 수집 현황"),
        ("reddit_analysis", "• Reddit 토픽 분석"),
        ("topic_cloud", "• Topic Cloud"),
        ("ai_overview", "• AI 오버뷰 분석"),
        ("master_topics", "• 마스터 토픽 제안")
    ]
    
    # 사이드바 네비게이션 메뉴 스타일 (링크 형태)
    st.markdown(
        """
        <style>
        /* 모든 사이드바 메뉴 버튼을 네비게이션 링크처럼 스타일링 */
        [data-testid="stSidebar"] .stButton {
            width: 100% !important;
            margin-bottom: 0 !important;
        }
        
        [data-testid="stSidebar"] .stButton {
            margin-bottom: 2px !important;
        }
        
        [data-testid="stSidebar"] .stButton > button {
            width: 100% !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            text-align: left !important;
            padding: 6px 0 6px 0 !important;
            color: #ffffff !important;
            font-weight: 400 !important;
            border-radius: 0 !important;
            margin-bottom: 0 !important;
            transition: all 0.2s ease !important;
            justify-content: flex-start !important;
            display: flex !important;
            align-items: center !important;
        }
        
        /* 텍스트 좌측 정렬 강제 */
        [data-testid="stSidebar"] .stButton > button > div {
            text-align: left !important;
            width: 100% !important;
        }
        
        [data-testid="stSidebar"] .stButton > button:hover {
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: #ffffff !important;
        }
        
        /* 선택된 메뉴 스타일 (둥근 사각형으로 감싸기) */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            color: #ff0000 !important;
            font-weight: 600 !important;
            background-color: rgba(255, 0, 0, 1) !important;
            border-radius: 8px !important;
            padding: 8px 12px 8px 12px !important;
        }
        
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            color: #ffffff !important;
            background-color: rgba(255, 0, 0, 1) !important;
        }
        
        /* 이모지 아이콘을 화이트 원톤으로 변경 - 이모지는 텍스트 색상을 따르므로 자동 적용됨 */
        /* 일반 메뉴: 화이트 (#ffffff) */
        /* 선택된 메뉴: 레드 (#ff4444) */
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 모든 메뉴를 네비게이션 링크 형태로 노출
    current_page = st.session_state.selected_page
    
    for page_id, page_label in page_options:
        # 현재 선택된 페이지인지 확인
        is_selected = (current_page == page_id)
        
        # 선택된 항목은 primary 버튼으로 표시 (레드 색상 적용)
        # 이모지는 텍스트 색상을 따르므로 CSS로 색상이 자동 적용됨
        if is_selected:
            if st.button(page_label, key=f"menu_{page_id}", use_container_width=True, type="primary"):
                st.session_state.selected_page = page_id
                st.rerun()
        else:
            if st.button(page_label, key=f"menu_{page_id}", use_container_width=True):
                st.session_state.selected_page = page_id
                st.rerun()
    
    # OpenAI API 키 설정 (환경변수가 없을 때만 표시)
    if not is_openai_available():
        st.markdown("### ⚙️ 설정")
        st.markdown("**OpenAI API 키**")
        st.caption("환경변수에 API 키가 설정되지 않았습니다.")
        
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
            st.info("💡 API 키가 입력되었습니다.")
    
    # 로고 이미지 (사이드바 하단)
    st.markdown(
        """
        <div style="margin-top: 180px; text-align: left;">
            <img src="https://i.namu.wiki/i/Ihw3UBmdSOTAo4ruNUZNFYLxrXSfu9MYuVPP3CYoxcxqKRyn4VHCF220shkikoTuq7tfAiUrgDJCPpAo4Q-Muw.webp" 
                 alt="LG Electronics Logo" 
                 style="max-width: 80%; height: auto; display: block;">
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================================
# 메인 콘텐츠 영역
# ============================================================================

# 다크 모드 CSS 적용 + 대시보드 타이포그래피 조정
st.markdown(
    """
    <style>
    /* 다크 모드 기본 스타일 - 사이드바 타이틀과 같은 높이에 맞춤 */
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* 메인 콘텐츠 영역의 모든 상단 여백 제거 */
    .main .block-container > div {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* 제목 스타일 다크 모드 최적화 + 크기 조정 */
    h1 {
        color: #ffffff !important;
        font-size: 1.5rem !important;
        margin-bottom: 0.5rem !important;
        line-height: 1.3 !important;
    }
    
    /* subheader (h2) 기본 스타일 */
    h2 {
        color: #ffffff !important;
        font-size: 1.2em !important;
        margin-bottom: 0rem !important;
        margin-top: 0rem !important;
        padding-top: 0rem !important;
        line-height: 1.6 !important;
        font-weight: 600 !important;
    }
    
    /* 사이드바 h2는 원래 크기 유지 (먼저 정의하여 우선순위 확보) */
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] .block-container h2,
    [data-testid="stSidebar"] div h2 {
        font-size: 1.2em !important;
    }
    
    /* 페이지 타이틀 전용 클래스 - 1.8배 크기 (기존 1.2em * 1.8 = 2.16em) */
    .page-title {
        font-size: 2.16em !important;
        font-weight: 600 !important;
        line-height: 1.6 !important;
        color: #ffffff !important;
        margin-bottom: 0rem !important;
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* 우측 본문 영역의 subheader만 1.8배 크기 (기존 방식 유지 - 호환성) */
    section[data-testid="stMain"] h2,
    section[data-testid="stMain"] .block-container h2,
    section[data-testid="stMain"] .block-container > div h2,
    section[data-testid="stMain"] .block-container > div > div h2,
    section[data-testid="stMain"] [data-testid="stVerticalBlock"] h2,
    section[data-testid="stMain"] .element-container h2,
    section[data-testid="stMain"] [data-testid="stVerticalBlock"] > [data-testid="element-container"] h2,
    section[data-testid="stMain"] [data-testid="stVerticalBlock"] > [data-testid="element-container"] > div h2,
    .main h2,
    .main .block-container h2,
    .main .block-container > div h2,
    .main .block-container > div > div h2,
    .main [data-testid="stVerticalBlock"] h2,
    .main .element-container h2 {
        font-size: 2.16em !important;
    }
    
    /* 첫 번째 subheader를 사이드바 타이틀과 정확히 같은 높이에 배치 */
    .main .block-container > div:first-child h2,
    .main .block-container > div:first-child > div h2,
    .main .block-container > div:first-child > div > div h2 {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* Streamlit의 기본 상단 여백 완전 제거 */
    .main .block-container > div:first-child > div:first-child,
    .main .block-container > div:first-child > div:first-child > div {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* element-container의 기본 마진 제거 */
    .main .block-container .element-container {
        margin-top: 0rem !important;
    }
    
    /* 첫 번째 element-container는 완전히 여백 제거 */
    .main .block-container > div:first-child .element-container:first-child {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* Streamlit의 모든 상단 여백 강제 제거 */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:first-child {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* 첫 번째 요소의 모든 래퍼 제거 */
    .main .block-container > div:first-child > * {
        margin-top: 0rem !important;
    }
    
    /* Streamlit의 기본 상단 패딩 완전 제거 */
    .main [data-testid="stVerticalBlock"]:first-child {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* 첫 번째 subheader의 모든 부모 요소 여백 제거 */
    .main .block-container > div:first-child * {
        margin-top: 0rem !important;
    }
    
    /* 첫 번째 h2만 예외적으로 유지 */
    .main .block-container > div:first-child h2:first-of-type {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* 사이드바와 메인 콘텐츠의 첫 번째 요소를 정확히 같은 높이에 배치 */
    .main .block-container > div:first-child {
        position: relative;
    }
    
    /* 첫 번째 subheader를 사이드바 타이틀과 정확히 같은 높이로 (음수 마진 사용) */
    .main .block-container > div:first-child h2:first-of-type {
        margin-top: -2rem !important;
        padding-top: 0rem !important;
    }
    
    h3 {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        margin-bottom: 0.4rem !important;
        margin-top: 0.8rem !important;
        line-height: 1.3 !important;
    }
    
    h4 {
        color: #ffffff !important;
        font-size: 0.95rem !important;
        margin-bottom: 0.3rem !important;
        margin-top: 0.6rem !important;
        line-height: 1.3 !important;
        font-weight: 600 !important;
    }
    
    /* 섹션 제목 (markdown ###) 크기 조정 */
    .element-container h3 {
        font-size: 1rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem !important;
        margin-top: 1rem !important;
    }
    
    /* 섹션 제목 (markdown ####) 크기 조정 */
    .element-container h4 {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.4rem !important;
        margin-top: 0.8rem !important;
    }
    
    /* 텍스트 색상 다크 모드 최적화 */
    p, div, span {
        color: #e0e0e0;
    }
    
    /* 캡션 색상 - 작고 회색 톤 */
    .stCaption {
        color: #888888 !important;
        font-size: 0.85rem !important;
        line-height: 1.4 !important;
    }
    
    /* 구분선 색상 */
    hr {
        border-color: #3d3d3d !important;
        margin: 0.8rem 0 !important;
    }
    
    /* 카드 간 여백 균일화 */
    .element-container {
        margin-bottom: 1rem !important;
    }
    
    /* Reddit 토픽 분석 페이지: 설명문과 탭 사이 간격 축소 (전역 CSS 오버라이드) */
    section[data-testid="stMain"] .element-container:has([data-testid="stCaption"]) {
        margin-bottom: 0.25rem !important;
    }
    
    section[data-testid="stMain"] .element-container:has([data-testid="stCaption"]) + .element-container,
    section[data-testid="stMain"] .element-container:has([data-testid="stCaption"]) ~ .element-container {
        margin-top: 0.25rem !important;
    }
    
    /* Expander 제목 크기 조정 */
    .streamlit-expanderHeader {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }
    
    /* Metric 카드 텍스트 크기 조정 */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 페이지별 콘텐츠 렌더링
selected_page = st.session_state.selected_page

if selected_page == "overview":
    render_overview()
    
elif selected_page == "exploration_status":
    st.markdown('<div class="page-title">• 구글 검색 결과 현황</div>', unsafe_allow_html=True)
    render_keyword_msv_stats()
    
elif selected_page == "reddit_collection_posts":
    st.markdown('<div class="page-title">• 레딧 게시물 수집 현황</div>', unsafe_allow_html=True)
    render_reddit_collection_posts()
    
elif selected_page == "reddit_analysis":
    st.markdown('<div class="page-title">• Reddit 토픽 분석</div>', unsafe_allow_html=True)
    render_clustering_results()
    
elif selected_page == "topic_cloud":
    st.markdown('<div class="page-title">• Topic Cloud</div>', unsafe_allow_html=True)
    render_topic_cloud()
    
elif selected_page == "ai_overview":
    st.markdown('<div class="page-title">• AI 오버뷰 분석</div>', unsafe_allow_html=True)
    render_trend_explorer()
    
elif selected_page == "master_topics":
    st.markdown('<div class="page-title">• LG전자 HS 마스터 토픽 제안</div>', unsafe_allow_html=True)
    render_master_topics()
