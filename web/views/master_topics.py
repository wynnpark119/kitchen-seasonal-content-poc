"""
Master Topics 뷰

마스터 토픽 JSON을 로드하고 표시하는 뷰
"""
import streamlit as st
import json
import os
import logging
import traceback
from pathlib import Path
from typing import Dict, Optional
import html
import hashlib

from services.gpt_service import get_gpt_service
from common.openai_client import is_openai_available, load_openai_api_key
from web.db_queries import get_master_topics
from common.file_loader import load_json
from common.path_utils import get_data_dir
import pandas as pd

# 로거 설정
logger = logging.getLogger(__name__)


def load_master_topics(path: Optional[str] = None) -> Optional[Dict]:
    """
    마스터 토픽 JSON 파일을 로드하는 함수 (하위 호환성 유지)
    
    Args:
        path: JSON 파일 경로 (선택사항, None이면 자동으로 찾음)
        
    Returns:
        Dict: 로드된 JSON 데이터, 실패 시 None
    """
    # 새로운 방식: 파일명만 지정하면 자동으로 찾음
    if path is None:
        # 우선순위: master_topics_final_kr_en_RICH_WHY.json -> master_topics.json
        data = load_json("master_topics_final_kr_en_RICH_WHY.json", required=False)
        if data is None:
            data = load_json("master_topics.json", required=False)
        return data
    
    # 기존 방식: 경로 직접 지정 (하위 호환성)
    try:
        file_path = Path(path)
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        logger.error(f"파일 로드 오류: {e}")
        return None


def load_master_topics_from_db() -> Optional[Dict]:
    """
    DB에서 마스터 토픽 데이터를 로드하여 JSON 형식으로 변환
    
    Returns:
        Dict: 카테고리별로 그룹화된 토픽 데이터, 실패 시 None
    """
    try:
        # DB에서 모든 마스터 토픽 가져오기
        df = get_master_topics()
        
        if df is None:
            logger.warning("get_master_topics() returned None")
            return None
            
        if len(df) == 0:
            logger.warning("get_master_topics() returned empty DataFrame")
            return None
            
        logger.info(f"DB에서 {len(df)}개의 마스터 토픽 로드됨")
        
        # 카테고리별로 그룹화
        topics_by_category = {}
        
        for category in df['category'].dropna().unique():
            category_df = df[df['category'] == category]
            topics_list = []
            
            for _, row in category_df.iterrows():
                # JSON 필드 파싱
                def parse_json_field(value, default):
                    if pd.isna(value) or value is None:
                        return default
                    if isinstance(value, (dict, list)):
                        return value
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except:
                            return default
                    return default
                
                topic = {
                    'topic_title': row.get('topic_title', ''),
                    'primary_question': row.get('primary_question', ''),
                    'related_questions': parse_json_field(row.get('related_questions_json'), []),
                    'score': float(row.get('score', 0)) if pd.notna(row.get('score')) else 0,
                    'evidence_score': row.get('evidence_score'),
                    'why_now': parse_json_field(row.get('why_now_json'), {}),
                    'blog_angle': row.get('blog_angle', ''),
                    'social_angle': row.get('social_angle', ''),
                    'evidence_pack': parse_json_field(row.get('evidence_pack_json'), {}),
                    'insights': parse_json_field(row.get('insights_json'), {}),
                    'cluster_size': int(row.get('cluster_size', 0)) if pd.notna(row.get('cluster_size')) else 0,
                }
                topics_list.append(topic)
            
            # 카테고리명을 JSON 키 형식으로 변환
            category_key = category
            topics_by_category[category_key] = topics_list
        
        return topics_by_category if topics_by_category else None
        
    except Exception as e:
        error_msg = f"DB에서 마스터 토픽 로드 오류: {e}"
        logger.error(error_msg)
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        # Streamlit에도 에러 표시
        st.error(f"❌ {error_msg}")
        st.code(error_trace, language='python')
        return None


def _add_card_css():
    """카드 스타일링 CSS를 한 번만 추가 (다크 모드 최적화)"""
    if 'topic_card_css_added' not in st.session_state:
        st.markdown(
            """
            <style>
            /* Expander 헤더 스타일 개선 */
            .streamlit-expanderHeader {
                font-size: 1.1rem !important;
                font-weight: 600 !important;
                color: #ffffff !important;
                padding: 0.75rem 1rem !important;
                background-color: #262730 !important;
                border-radius: 8px !important;
                border: 1px solid #3d3d3d !important;
                transition: all 0.2s ease !important;
            }
            
            /* Expander 간 간격 최소화 */
            .element-container:has(.streamlit-expander) {
                margin-bottom: 0.25rem !important;
            }
            
            .streamlit-expander {
                margin-bottom: 0.25rem !important;
            }
            
            /* Expander 래퍼 간격 제거 */
            div[data-testid="stExpander"] {
                margin-bottom: 0.25rem !important;
            }
            
            .streamlit-expanderHeader:hover {
                background-color: #2f2f3a !important;
                border-color: #4d4d5d !important;
            }
            
            /* Expander 콘텐츠 영역 스타일 */
            .streamlit-expanderContent {
                padding: 1.25rem 1rem !important;
                background-color: #1e1e28 !important;
                border-radius: 0 0 8px 8px !important;
                border: 1px solid #3d3d3d !important;
                border-top: none !important;
                margin-top: 0 !important;
            }
            
            /* Expander 내부 섹션 제목 스타일 */
            .streamlit-expanderContent h3,
            .streamlit-expanderContent h4 {
                color: #ffffff !important;
                font-weight: 600 !important;
                margin-top: 1.5rem !important;
                margin-bottom: 0.75rem !important;
                font-size: 0.95rem !important;
                text-transform: uppercase !important;
                letter-spacing: 0.5px !important;
            }
            
            .streamlit-expanderContent h3:first-child,
            .streamlit-expanderContent h4:first-child {
                margin-top: 0 !important;
            }
            
            /* Expander 내부 텍스트 스타일 */
            .streamlit-expanderContent p,
            .streamlit-expanderContent div {
                color: #e0e0e0 !important;
                line-height: 1.7 !important;
            }
            
            /* Caption 스타일 개선 */
            .streamlit-expanderContent .stCaption {
                color: #b0b0b0 !important;
                font-size: 0.9rem !important;
                line-height: 1.6 !important;
                margin-top: 0.5rem !important;
                margin-bottom: 1rem !important;
            }
            
            /* 강조 텍스트 (이탤릭) 스타일 */
            .streamlit-expanderContent .stCaption em,
            .streamlit-expanderContent em {
                color: #c0c0c0 !important;
                font-style: italic !important;
            }
            
            /* 섹션 간 구분선 */
            .streamlit-expanderContent hr {
                border-color: #3d3d3d !important;
                margin: 1.5rem 0 !important;
            }
            
            /* 버튼 스타일 개선 */
            .streamlit-expanderContent .stButton > button {
                background-color: #ff0000 !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 0.5rem 1rem !important;
                font-weight: 500 !important;
                transition: all 0.2s ease !important;
            }
            
            .streamlit-expanderContent .stButton > button:hover {
                background-color: #ff3333 !important;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(255, 0, 0, 0.3) !important;
            }
            
            /* 경고/정보 메시지 스타일 */
            .streamlit-expanderContent .stWarning,
            .streamlit-expanderContent .stInfo,
            .streamlit-expanderContent .stError {
                border-radius: 6px !important;
                padding: 0.75rem 1rem !important;
            }
            
            /* Spinner 스타일 */
            .streamlit-expanderContent .stSpinner > div {
                color: #ffffff !important;
            }
            
            /* 코드 블록 스타일 */
            .streamlit-expanderContent code {
                background-color: #2a2a35 !important;
                color: #e0e0e0 !important;
                border: 1px solid #3d3d3d !important;
                border-radius: 4px !important;
                padding: 0.25rem 0.5rem !important;
            }
            
            /* 카테고리 섹션 제목 스타일 (h4) */
            .main h4 {
                color: #ffffff !important;
                font-size: 1.1rem !important;
                font-weight: 600 !important;
                margin-top: 2rem !important;
                margin-bottom: 1rem !important;
                padding-bottom: 0.5rem !important;
                border-bottom: 2px solid #3d3d3d !important;
            }
            
            /* 첫 번째 카테고리 제목 여백 조정 */
            .main h4:first-of-type {
                margin-top: 1rem !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.session_state['topic_card_css_added'] = True


def _get_topic_cache_key(category_key: str, master_topic_kr: str, prompt_version: str = "planning_v2") -> str:
    """토픽별 캐시 키 생성"""
    # 프롬프트 버전 추가 (프롬프트 변경 시 캐시 무효화)
    key_string = f"{prompt_version}_{category_key}_{master_topic_kr}"
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


def render_topic_card(topic: Dict, index: int, category_key: str):
    """
    개별 토픽을 카드 형태로 렌더링 (Streamlit 네이티브 컴포넌트 사용)
    
    Args:
        topic: 토픽 딕셔너리
        index: 토픽 인덱스 (1부터 시작)
        category_key: 카테고리 키 (예: "SPRING_RECIPES")
    """
    # 데이터 추출
    master_topic_kr = topic.get('master_topic_kr', 'N/A')
    master_topic_en = topic.get('master_topic_en', '')
    why_now_kr = topic.get('why_now_kr', '')
    why_now_en = topic.get('why_now_en', '')
    content_angle = topic.get('content_angle', '')
    related_topics = topic.get('related_topics', [])
    
    # 카테고리 이름을 읽기 쉽게 변환
    category_display = category_key.replace('_', ' ').title()
    
    # 프롬프트 버전 (캐시 무효화용)
    prompt_version = "planning_v3_content_planner"
    
    # 캐시 키 생성 (프롬프트 버전 포함)
    cache_key = f"hs_insight_{_get_topic_cache_key(category_key, master_topic_kr, prompt_version)}"
    button_key = f"hs_insight_btn_{category_key}_{index}"
    
    # Expander를 사용한 카드 형태
    with st.expander(f"{index}. {master_topic_kr}", expanded=False):
        # 선정 이유 (한국어 - 영어 순서)
        if why_now_kr or why_now_en:
            st.markdown("#### 선정 이유")
            if why_now_kr:
                st.caption(why_now_kr)
            if why_now_en:
                st.caption(why_now_en)
        
        # 콘텐츠 전략
        if content_angle:
            st.markdown("#### 콘텐츠 전략")
            st.caption(content_angle)
        
        # 연관 주제
        if related_topics:
            topics_text = " · ".join(related_topics)
            st.markdown("#### 연관 주제")
            st.caption(topics_text)
        
        # AI 콘텐츠 플래닝 버튼 및 출력 (연관 주제 바로 아래)
        # API 키 확인 (선제 차단)
        api_key = load_openai_api_key()
        if not api_key:
            st.warning("⚠️ OPENAI_API_KEY가 설정되어 있지 않습니다. 환경변수 또는 사이드바에서 입력하세요.")
            # 사이드바에 API 키 입력 제공 (선택)
            with st.sidebar:
                if 'openai_api_key_input' not in st.session_state:
                    st.session_state.openai_api_key_input = ""
                
                api_key_input = st.text_input(
                    "OpenAI API Key",
                    value=st.session_state.openai_api_key_input,
                    type="password",
                    help="환경변수 OPENAI_API_KEY가 없을 때만 사용됩니다.",
                    key=f"openai_api_key_sidebar_{button_key}"
                )
                
                if api_key_input and api_key_input != st.session_state.openai_api_key_input:
                    os.environ["OPENAI_API_KEY"] = api_key_input
                    st.session_state.openai_api_key_input = api_key_input
                    from common.openai_client import reset_client
                    reset_client()
                    st.success("✅ API 키가 설정되었습니다. 버튼을 다시 클릭하세요.")
                    st.rerun()
        elif is_openai_available():
            # 캐시 초기화 (필요시)
            if "hs_insight_cache" not in st.session_state:
                st.session_state.hs_insight_cache = {}
            
            # 프롬프트 버전 확인 및 캐시 무효화
            cache_version_key = f"{cache_key}_version"
            cached_version = st.session_state.get(cache_version_key, None)
            
            # 버전이 다르면 캐시 무효화
            if cached_version != prompt_version:
                if cache_key in st.session_state.hs_insight_cache:
                    del st.session_state.hs_insight_cache[cache_key]
                st.session_state[cache_version_key] = prompt_version
            
            # 캐시에서 결과 확인
            cached_result = st.session_state.hs_insight_cache.get(cache_key)
            show_insight_key = f"{cache_key}_show"
            should_show = st.session_state.get(show_insight_key, False)
            
            # 버튼 표시 (캐시가 있으면 다른 텍스트)
            if cached_result:
                button_label = "🔄 AI 콘텐츠 플래닝 다시 생성하기"
            else:
                button_label = "🔍 AI 콘텐츠 플래닝"
            
            button_clicked = st.button(
                button_label,
                key=button_key,
                type="primary"
            )
            
            # 버튼 클릭 시 캐시 삭제 및 새로 생성
            if button_clicked:
                st.session_state[show_insight_key] = True
                # 캐시 완전 삭제
                if cache_key in st.session_state.hs_insight_cache:
                    del st.session_state.hs_insight_cache[cache_key]
                # 강제 재생성 플래그 설정
                st.session_state[f"{cache_key}_force_regenerate"] = True
                # 캐시 결과 초기화
                cached_result = None
                # 버전도 재설정하여 새로 생성되도록 함
                st.session_state[cache_version_key] = prompt_version
            
            # 강제 재생성 플래그 확인
            force_regenerate = st.session_state.get(f"{cache_key}_force_regenerate", False)
            
            # 캐시 다시 확인 (버튼 클릭 시 삭제되었을 수 있음)
            cached_result = st.session_state.hs_insight_cache.get(cache_key)
            
            # 표시할지 결정 (버튼 클릭했거나 이미 표시 중이거나 캐시가 있으면 표시)
            if button_clicked or should_show or (cached_result and not force_regenerate):
                if cached_result and not force_regenerate and not button_clicked:
                    # 캐시된 결과 표시 (버튼 클릭이 아니고 강제 재생성 요청이 없을 때만)
                    st.markdown("---")
                    st.markdown("#### AI 콘텐츠 플래닝")
                    st.caption(cached_result)
                    st.caption("💡 새로운 인사이트를 생성하려면 '다시 생성하기' 버튼을 클릭하세요.")
                elif button_clicked or force_regenerate or not cached_result:
                    # GPT 호출 (버튼 클릭 시에만, 캐시가 없을 때)
                    with st.spinner("⏳ AI 콘텐츠 플래닝 생성 중..."):
                        error_traceback_str = None
                        try:
                            # 데이터 검증 및 디버깅
                            logger.debug(f"Generating insight for topic: {master_topic_kr}")
                            logger.debug(f"Category: {category_key}")
                            logger.debug(f"Related topics: {related_topics}")
                            
                            # 빈 값 처리
                            safe_master_topic_kr = master_topic_kr or "N/A"
                            safe_master_topic_en = master_topic_en or ""
                            safe_why_now_kr = why_now_kr or ""
                            safe_why_now_en = why_now_en or ""
                            safe_content_angle = content_angle or ""
                            safe_related_topics = related_topics[:3] if related_topics else []
                            
                            # GPT 서비스 가져오기 (강제 리로드 및 모듈 재import)
                            import importlib
                            import services.gpt_service as gpt_service_module
                            from services.gpt_service import reset_gpt_service
                            
                            # 모듈 강제 리로드
                            importlib.reload(gpt_service_module)
                            reset_gpt_service()  # 이전 인스턴스 제거
                            
                            # 리로드된 모듈에서 다시 import
                            from services.gpt_service import get_gpt_service
                            gpt_service = get_gpt_service()
                            logger.debug("GPT service instance created successfully")
                            
                            # 메서드 존재 확인
                            if not hasattr(gpt_service, 'generate_hs_insight'):
                                error_msg = "GPT 서비스에 generate_hs_insight 메서드가 없습니다. 앱을 재시작해주세요."
                                logger.error(error_msg)
                                st.error("⚠️ " + error_msg)
                                st.info("💡 Streamlit 앱을 재시작하면 해결됩니다.")
                                raise AttributeError(error_msg)
                            
                            # 인사이트 생성 (prompt_version 전달 시도, 실패하면 기본값 사용)
                            try:
                                # prompt_version을 포함하여 호출 시도
                                insight, error_msg, debug_info = gpt_service.generate_hs_insight(
                                    topic_category=category_key,
                                    master_topic_kr=safe_master_topic_kr,
                                    master_topic_en=safe_master_topic_en,
                                    why_now_kr=safe_why_now_kr,
                                    why_now_en=safe_why_now_en,
                                    content_angle=safe_content_angle,
                                    related_topics=safe_related_topics,
                                    prompt_version=prompt_version
                                )
                            except TypeError as e:
                                # prompt_version 파라미터가 없으면 기본값 사용
                                logger.warning(f"prompt_version 파라미터 전달 실패, 기본값 사용: {e}")
                                try:
                                    insight, error_msg, debug_info = gpt_service.generate_hs_insight(
                                        topic_category=category_key,
                                        master_topic_kr=safe_master_topic_kr,
                                        master_topic_en=safe_master_topic_en,
                                        why_now_kr=safe_why_now_kr,
                                        why_now_en=safe_why_now_en,
                                        content_angle=safe_content_angle,
                                        related_topics=safe_related_topics
                                    )
                                    # debug_info는 사용하지 않으므로 None으로 설정
                                    debug_info = None
                                except Exception as e2:
                                    error_msg = f"인사이트 생성 실패: {str(e2)}"
                                    logger.exception("Error generating insight")
                                    debug_info = None
                                    insight, error_msg, debug_info = None, error_msg, debug_info
                            
                            if insight:
                                # 캐시에 저장 및 강제 재생성 플래그 제거
                                st.session_state.hs_insight_cache[cache_key] = insight
                                st.session_state[show_insight_key] = True
                                st.session_state[f"{cache_key}_force_regenerate"] = False
                                st.markdown("---")
                                st.markdown("#### AI 콘텐츠 플래닝")
                                st.caption(insight)
                            elif error_msg:
                                # 에러 메시지가 있는 경우
                                st.error("⚠️ 인사이트 생성 중 오류가 발생했습니다. 아래 상세 오류를 확인하세요.")
                                
                                # 사용자 친화적인 메시지
                                if "API 키" in error_msg or "인증" in error_msg or "401" in error_msg:
                                    st.warning("💡 API 키가 유효하지 않습니다. 사이드바에서 다시 입력하세요.")
                                elif "사용량 제한" in error_msg or "429" in error_msg or "rate limit" in error_msg.lower():
                                    st.info("💡 API 사용량 제한에 도달했습니다. 잠시 후 다시 시도해주세요.")
                                elif "시간 초과" in error_msg or "timeout" in error_msg.lower():
                                    st.info("💡 요청 시간이 초과되었습니다. 네트워크 연결을 확인하고 다시 시도해주세요.")
                                elif "연결" in error_msg or "connection" in error_msg.lower():
                                    st.info("💡 네트워크 연결 오류가 발생했습니다. 인터넷 연결을 확인해주세요.")
                                
                                # 상세 오류 보기 expander
                                with st.expander("🔍 상세 오류 보기"):
                                    st.code(error_msg)
                                    
                        except Exception as e:
                            # 예외 발생 시 전체 traceback 캡처
                            error_traceback_str = traceback.format_exc()
                            error_type = type(e).__name__
                            error_msg = str(e)
                            
                            # 서버 콘솔에 전체 예외 로깅
                            logger.exception("Error generating HS insight")
                            
                            # UI에 사용자 친화적 메시지
                            st.error("⚠️ 인사이트 생성 중 오류가 발생했습니다. 아래 상세 오류를 확인하세요.")
                            
                            # 상세 오류 보기 expander
                            with st.expander("🔍 상세 오류 보기"):
                                st.code(error_traceback_str)
                                
                                # 추가 정보
                                st.markdown("**오류 정보:**")
                                st.text(f"오류 타입: {error_type}")
                                st.text(f"오류 메시지: {error_msg}")
                                st.text(f"토픽: {master_topic_kr}")
                                st.text(f"카테고리: {category_key}")
        else:
            st.warning("⚠️ OpenAI API 키가 설정되지 않아 인사이트를 생성할 수 없습니다.")


def render_category_section(category_key: str, topics: list):
    """
    카테고리 섹션을 렌더링
    
    Args:
        category_key: 카테고리 키 (예: "SPRING_RECIPES")
        topics: 해당 카테고리의 토픽 리스트
    """
    # 토픽 카드 렌더링
    if topics:
        for idx, topic in enumerate(topics, start=1):
            render_topic_card(topic, idx, category_key)
            # 카드 간 간격 추가 (마지막 카드 제외, 간격 최소화)
            if idx < len(topics):
                st.markdown("<div style='margin-bottom: 0.25rem;'></div>", unsafe_allow_html=True)
    else:
        st.info("이 카테고리에 토픽이 없습니다.")


def render_master_topics():
    """Master Topics 탭 렌더링"""
    # CSS 스타일 추가
    _add_card_css()
    
    # 새로운 방식: 공통 파일 로더 사용
    topics_data = load_master_topics()  # path=None이면 자동으로 찾음
    
    # JSON 파일이 없거나 로드 실패 시에만 DB에서 로드 (fallback)
    if topics_data is None:
        st.warning("⚠️ JSON 파일을 찾을 수 없어 DB에서 마스터 토픽 데이터를 불러오는 중...")
        with st.spinner("DB에서 데이터 로드 중..."):
            topics_data = load_master_topics_from_db()
        
        if topics_data is None:
            # DB 연결 테스트 및 상태 확인
            db_connected = False
            table_exists = False
            record_count = 0
            
            try:
                from web.db_queries import get_db_connection
                conn = get_db_connection()
                if conn:
                    db_connected = True
                    st.info("✅ DB 연결은 정상입니다.")
                    # 테이블 존재 여부 확인
                    try:
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT COUNT(*) 
                                FROM information_schema.tables 
                                WHERE table_name = 'topic_qa_briefs'
                            """)
                            table_exists = cur.fetchone()[0] > 0
                            if table_exists:
                                cur.execute("SELECT COUNT(*) FROM topic_qa_briefs")
                                record_count = cur.fetchone()[0]
                                st.info(f"📊 topic_qa_briefs 테이블 존재: {table_exists}, 레코드 수: {record_count}")
                            else:
                                st.warning("⚠️ topic_qa_briefs 테이블이 존재하지 않습니다.")
                        conn.close()
                    except Exception as e:
                        st.error(f"테이블 확인 중 오류: {e}")
                else:
                    st.error("❌ DB 연결 실패")
            except Exception as e:
                st.error(f"DB 연결 테스트 중 오류: {e}")
            
            # 데이터가 없는 경우 안내
            data_dir = get_data_dir()
            if db_connected and table_exists and record_count == 0:
                st.warning("⚠️ topic_qa_briefs 테이블에 데이터가 없습니다.")
                st.info("💡 **해결 방법:**")
                st.info("1. Worker 파이프라인을 실행하여 마스터 토픽 데이터를 생성하세요.")
                st.info(f"2. 또는 다음 경로에 JSON 파일을 배치하세요:")
                st.text(f"   - {data_dir / 'master_topics_final_kr_en_RICH_WHY.json'}")
                st.text(f"   - {data_dir / 'master_topics.json'}")
                
                # 빈 상태 UI 표시
                st.markdown("---")
                st.info("📝 현재 데이터가 없어 마스터 토픽을 표시할 수 없습니다.")
                return
            else:
                st.error("❌ 마스터 토픽 데이터를 로드할 수 없습니다.")
                st.info("다음 사항을 확인해주세요:")
                st.info("1. DB 연결 상태 확인")
                st.info("2. topic_qa_briefs 테이블에 데이터가 있는지 확인")
                st.info(f"3. 또는 다음 경로에 JSON 파일을 배치해주세요:")
                st.text(f"   - {data_dir / 'master_topics_final_kr_en_RICH_WHY.json'}")
                st.text(f"   - {data_dir / 'master_topics.json'}")
                return
        else:
            total_topics = sum(len(v) for v in topics_data.values())
            st.success(f"✅ DB에서 {total_topics}개의 마스터 토픽을 불러왔습니다. ({len(topics_data)}개 카테고리)")
    
    # 데이터 형식 검증: 각 카테고리가 리스트인지 확인
    if isinstance(topics_data, dict):
        for category_key, category_data in topics_data.items():
            if not isinstance(category_data, list):
                st.error(f"⚠️ '{category_key}' 카테고리의 데이터 형식이 올바르지 않습니다.")
                st.info("마스터 토픽 파일은 각 카테고리가 토픽 객체의 리스트여야 합니다.")
                return
    
    # ========================================================================
    # 마스터 토픽 인사이트 Overview
    # ========================================================================
    # 카테고리 정의 (탭 생성 전에 미리 정의)
    categories = [
        "SPRING_RECIPES",
        "SPRING_KITCHEN_STYLING",
        "REFRIGERATOR_ORGANIZATION",
        "VEGETABLE_PREP_HANDLING"
    ]
    
    category_labels = {
        "SPRING_RECIPES": "Spring Recipes",
        "SPRING_KITCHEN_STYLING": "Spring Kitchen Styling",
        "REFRIGERATOR_ORGANIZATION": "Refrigerator Organization",
        "VEGETABLE_PREP_HANDLING": "Vegetable Prep & Handling"
    }
    
    # 존재하는 카테고리만 필터링
    available_categories = [cat for cat in categories if cat in topics_data] if topics_data else []
    
    with st.expander("마스터 토픽 인사이트 Overview", expanded=False):
        st.markdown("""
봄 시즌 주방에서 나타나는 변화는 새로운 트렌드의 등장이라기보다,  
기존 생활 방식이 더 이상 잘 작동하지 않는 순간에 대한 반응에 가깝습니다.  
고객은 '새로 해보고 싶어서' 움직이기보다, 지금의 방식이 맞지 않다는 불편을 해소하려고 움직입니다.

이번 마스터 토픽은 바로 그 지점에서 갈라진 문제들을 정리한 결과입니다.

---

**Spring Recipes** <span id="overview-link-spring-recipes" class="overview-link-icon" style="cursor: pointer; opacity: 0.5; margin-left: 8px; font-size: 0.5em; transform: scale(0.5); display: inline-block; vertical-align: middle;" title="Spring Recipes 탭으로 이동">🔗</span>

봄 레시피에 대한 관심은 '가벼운 요리'에 대한 욕망이 아니라,  
가벼운 식단이 반복해서 실패해온 경험에 대한 보완 욕구로 나타납니다.  
그래서 레시피 추천보다  
왜 봄철 식단 전환이 만족스럽지 않은지,  
어디서 허기와 번거로움이 생기는지를 짚는 주제가 중심이 됩니다.

→ 이 카테고리는 요리 아이디어가 아니라  
저녁 식사 루틴을 가볍게 재설계하려는 흐름을 담고 있습니다.

---

**Refrigerator Organization** <span id="overview-link-refrigerator" class="overview-link-icon" style="cursor: pointer; opacity: 0.5; margin-left: 8px; font-size: 0.5em; transform: scale(0.5); display: inline-block; vertical-align: middle;" title="Refrigerator Organization 탭으로 이동">🔗</span>

냉장고 정리는 '정리법'의 문제가 아니라  
유지되지 않는 구조에 대한 반복적인 좌절로 인식됩니다.  
정리는 했지만 며칠 지나 무너지는 경험이 누적되면서,  
고객의 관심은 팁에서 구조와 루틴으로 이동합니다.

→ 이 주제는 정리 노하우가 아니라  
냉장고가 무너지는 패턴 자체를 다시 설계하려는 시도입니다.

---

**Vegetable Prep & Handling** <span id="overview-link-vegetable" class="overview-link-icon" style="cursor: pointer; opacity: 0.5; margin-left: 8px; font-size: 0.5em; transform: scale(0.5); display: inline-block; vertical-align: middle;" title="Vegetable Prep & Handling 탭으로 이동">🔗</span>

채소 관련 고민은 구매보다  
손질 이후, 보관 이후, 시간이 지난 시점에 집중됩니다.  
Meal Prep이 실패하는 이유 역시 의지나 계획이 아니라,  
채소가 계획을 망치는 변수로 작동하기 때문입니다.

→ 이 카테고리는 채소를 '잘 다루는 법'이 아니라  
식단 계획을 무너뜨리지 않게 관리하는 방법에 대한 탐색입니다.

---

**Spring Kitchen Styling** <span id="overview-link-styling" class="overview-link-icon" style="cursor: pointer; opacity: 0.5; margin-left: 8px; font-size: 0.5em; transform: scale(0.5); display: inline-block; vertical-align: middle;" title="Spring Kitchen Styling 탭으로 이동">🔗</span>

봄철 주방 스타일링은 변화에 대한 욕구와  
관리 부담에 대한 현실 사이의 타협으로 나타납니다.  
크게 바꾸기보다 작게 바꾸고, 오래 유지하려는 방향이 선호됩니다.

→ 이 주제는 인테리어가 아니라  
일상 속에서 유지 가능한 분위기 전환에 초점이 맞춰져 있습니다.
        """)
        
        # 링크 아이콘 호버 효과 및 섹션 타이틀 크기 조정을 위한 CSS
        st.markdown("""
        <style>
        /* Overview 섹션 내의 섹션 타이틀 크기 증가 */
        .streamlit-expanderContent strong {
            font-size: 1.3em !important;
            font-weight: 600 !important;
        }
        
        #overview-link-spring-recipes:hover,
        #overview-link-refrigerator:hover,
        #overview-link-vegetable:hover,
        #overview-link-styling:hover {
            opacity: 1 !important;
            color: #ff0000 !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if available_categories:
        # 탭 생성
        tab_labels = [category_labels[cat] for cat in available_categories]
        tabs = st.tabs(tab_labels)
        
        # 탭 생성 후 링크 클릭 이벤트를 위한 JavaScript 추가
        st.markdown("""
        <script>
        (function() {
            // 카테고리별 탭 라벨 매핑
            const categoryToTabLabel = {
                'spring-recipes': 'Spring Recipes',
                'refrigerator': 'Refrigerator Organization',
                'vegetable': 'Vegetable Prep & Handling',
                'styling': 'Spring Kitchen Styling'
            };
            
            // 탭 라벨로 탭 찾기 및 클릭
            function clickTabByLabel(tabLabel) {
                // 모든 탭 컨테이너 찾기
                const tabContainers = document.querySelectorAll('[data-testid="stTabs"]');
                if (!tabContainers || tabContainers.length === 0) {
                    console.log('탭 컨테이너를 찾을 수 없습니다');
                    return;
                }
                
                // 마지막 탭 컨테이너 사용 (Master Topics 페이지의 탭)
                const lastTabContainer = tabContainers[tabContainers.length - 1];
                const tabs = lastTabContainer.querySelectorAll('button[role="tab"]');
                
                if (!tabs || tabs.length === 0) {
                    console.log('탭 버튼을 찾을 수 없습니다');
                    return;
                }
                
                // 탭 버튼의 텍스트 내용으로 찾기 (부분 매칭 포함)
                for (let i = 0; i < tabs.length; i++) {
                    const tabText = tabs[i].textContent.trim();
                    // 정확히 일치하거나 포함하는 경우
                    if (tabText === tabLabel || tabText.includes(tabLabel)) {
                        console.log('탭 찾음:', tabText, '인덱스:', i);
                        tabs[i].click();
                        // 탭으로 스크롤
                        setTimeout(() => {
                            tabs[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }, 100);
                        return true;
                    }
                }
                console.log('탭을 찾을 수 없습니다:', tabLabel);
                return false;
            }
            
            // 링크 아이콘에 클릭 이벤트 추가
            function setupLinks() {
                const linkSpring = document.getElementById('overview-link-spring-recipes');
                const linkRefrigerator = document.getElementById('overview-link-refrigerator');
                const linkVegetable = document.getElementById('overview-link-vegetable');
                const linkStyling = document.getElementById('overview-link-styling');
                
                if (linkSpring && !linkSpring.dataset.listenerAdded) {
                    linkSpring.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Spring Recipes 링크 클릭');
                        clickTabByLabel(categoryToTabLabel['spring-recipes']);
                    });
                    linkSpring.dataset.listenerAdded = 'true';
                }
                
                if (linkRefrigerator && !linkRefrigerator.dataset.listenerAdded) {
                    linkRefrigerator.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Refrigerator Organization 링크 클릭');
                        clickTabByLabel(categoryToTabLabel['refrigerator']);
                    });
                    linkRefrigerator.dataset.listenerAdded = 'true';
                }
                
                if (linkVegetable && !linkVegetable.dataset.listenerAdded) {
                    linkVegetable.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Vegetable Prep & Handling 링크 클릭');
                        clickTabByLabel(categoryToTabLabel['vegetable']);
                    });
                    linkVegetable.dataset.listenerAdded = 'true';
                }
                
                if (linkStyling && !linkStyling.dataset.listenerAdded) {
                    linkStyling.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Spring Kitchen Styling 링크 클릭');
                        clickTabByLabel(categoryToTabLabel['styling']);
                    });
                    linkStyling.dataset.listenerAdded = 'true';
                }
            }
            
            // 즉시 실행
            setupLinks();
            
            // Streamlit이 동적으로 콘텐츠를 로드할 수 있으므로 MutationObserver 사용
            const observer = new MutationObserver(function(mutations) {
                setupLinks();
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            // 추가 안전장치: 여러 번 시도
            setTimeout(setupLinks, 100);
            setTimeout(setupLinks, 500);
            setTimeout(setupLinks, 1000);
            setTimeout(setupLinks, 2000);
        })();
        </script>
        """, unsafe_allow_html=True)
        
        for tab, category_key in zip(tabs, available_categories):
            with tab:
                render_category_section(category_key, topics_data[category_key])
    else:
        st.warning("카테고리별 데이터가 없습니다.")
