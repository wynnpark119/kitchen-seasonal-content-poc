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

# 로거 설정
logger = logging.getLogger(__name__)


def load_master_topics(path: str) -> Optional[Dict]:
    """
    마스터 토픽 JSON 파일을 로드하는 함수
    
    Args:
        path: JSON 파일 경로
        
    Returns:
        Dict: 로드된 JSON 데이터, 실패 시 None
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        st.error(f"JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        st.error(f"파일 로드 오류: {e}")
        return None


def _add_card_css():
    """카드 스타일링 CSS를 한 번만 추가"""
    if 'topic_card_css_added' not in st.session_state:
        st.markdown(
            """
            <style>
            .topic-card-container {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 16px;
                padding: 2.25rem;
                margin-bottom: 2.5rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06);
                transition: all 0.3s ease;
            }
            .topic-card-container:hover {
                box-shadow: 0 8px 24px rgba(0,0,0,0.15), 0 4px 8px rgba(0,0,0,0.1);
                transform: translateY(-2px);
            }
            .card-header {
                border-bottom: 2px solid #f3f4f6;
                padding-bottom: 1.5rem;
                margin-bottom: 1.5rem;
            }
            .topic-title {
                font-size: 1.5rem;
                font-weight: 700;
                color: #111827;
                margin-bottom: 0.75rem;
                line-height: 1.4;
            }
            .topic-subtitle {
                font-size: 1.05rem;
                color: #6b7280;
                font-style: italic;
                margin-bottom: 1rem;
                line-height: 1.5;
            }
            .category-badge {
                display: inline-block;
                background-color: #eff6ff;
                color: #1e40af;
                padding: 0.375rem 0.875rem;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 0.5rem;
            }
            .topic-section {
                margin: 2rem 0;
            }
            .topic-section-title {
                font-size: 0.95rem;
                font-weight: 700;
                color: #374151;
                margin-bottom: 1rem;
                text-transform: uppercase;
                letter-spacing: 0.8px;
            }
            .topic-content {
                font-size: 1rem;
                color: #4b5563;
                line-height: 1.85;
                margin-bottom: 0;
                white-space: pre-wrap;
                word-wrap: break-word;
                max-width: 100%;
                overflow-wrap: break-word;
            }
            .topic-content-en {
                font-size: 0.95rem;
                color: #6b7280;
                font-style: italic;
                line-height: 1.75;
                white-space: pre-wrap;
                word-wrap: break-word;
                max-width: 100%;
                overflow-wrap: break-word;
            }
            .topic-divider {
                border-top: 1px solid #e5e7eb;
                margin: 2rem 0;
            }
            .related-topics {
                background-color: #f9fafb;
                border-left: 4px solid #3b82f6;
                padding: 1rem 1.25rem;
                margin-top: 2rem;
                border-radius: 6px;
            }
            .related-topics-text {
                font-size: 0.9rem;
                color: #6b7280;
                margin: 0;
                line-height: 1.7;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.session_state['topic_card_css_added'] = True


def _get_topic_cache_key(category_key: str, master_topic_kr: str) -> str:
    """토픽별 캐시 키 생성"""
    key_string = f"{category_key}_{master_topic_kr}"
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
    
    # 캐시 키 생성
    cache_key = f"hs_insight_{_get_topic_cache_key(category_key, master_topic_kr)}"
    button_key = f"hs_insight_btn_{category_key}_{index}"
    
    # Expander를 사용한 카드 형태
    with st.expander(f"{index}. {master_topic_kr}", expanded=False):
        # 영어 제목
        if master_topic_en:
            st.markdown(f"*{master_topic_en}*")
        
        # 카테고리 배지
        st.caption(f"📌 {category_display}")
        
        st.markdown("---")
        
        # WHY NOW (KR)
        if why_now_kr:
            st.markdown("**Why Now (KR)**")
            st.write(why_now_kr)
            st.markdown("")
        
        # WHY NOW (EN)
        if why_now_en:
            st.markdown("**Why Now (EN)**")
            st.write(why_now_en)
            st.markdown("")
        
        # Content Angle
        if content_angle:
            st.markdown("**Content Angle**")
            st.write(f"• {content_angle}")
            st.markdown("")
        
        # 연관 주제
        if related_topics:
            topics_text = " · ".join(related_topics)
            st.info(f"**연관 주제:** {topics_text}")
        
        # LG HS 인사이트 버튼 및 출력 (연관 주제 바로 아래)
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
            
            # 캐시에서 결과 확인
            cached_result = st.session_state.hs_insight_cache.get(cache_key)
            show_insight_key = f"{cache_key}_show"
            should_show = st.session_state.get(show_insight_key, False)
            
            # 버튼 표시 (캐시가 있으면 다른 텍스트)
            if cached_result:
                button_label = "🔄 LG전자 HS 콘텐츠 인사이트 다시 보기"
            else:
                button_label = "🔍 LG전자 HS 콘텐츠 인사이트 보기"
            
            button_clicked = st.button(
                button_label,
                key=button_key,
                type="primary"
            )
            
            # 버튼 클릭 시 표시 플래그 설정
            if button_clicked:
                st.session_state[show_insight_key] = True
            
            # 표시할지 결정 (버튼 클릭했거나 이미 표시 중이거나 캐시가 있으면 표시)
            if button_clicked or should_show or cached_result:
                if cached_result:
                    # 캐시된 결과 표시
                    st.markdown("### 📌 LG HS Strategic Content Insight")
                    st.markdown(cached_result)
                elif button_clicked:
                    # GPT 호출 (버튼 클릭 시에만, 캐시가 없을 때)
                    with st.spinner("⏳ LG HS 관점 인사이트 생성 중..."):
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
                            
                            # GPT 서비스 가져오기
                            gpt_service = get_gpt_service()
                            logger.debug("GPT service instance created successfully")
                            
                            # 메서드 존재 확인
                            if not hasattr(gpt_service, 'generate_hs_insight'):
                                error_msg = "GPT 서비스에 generate_hs_insight 메서드가 없습니다. 앱을 재시작해주세요."
                                logger.error(error_msg)
                                st.error("⚠️ " + error_msg)
                                st.info("💡 Streamlit 앱을 재시작하면 해결됩니다.")
                                raise AttributeError(error_msg)
                            
                            # 인사이트 생성
                            insight, error_msg = gpt_service.generate_hs_insight(
                                topic_category=category_key,
                                master_topic_kr=safe_master_topic_kr,
                                master_topic_en=safe_master_topic_en,
                                why_now_kr=safe_why_now_kr,
                                why_now_en=safe_why_now_en,
                                content_angle=safe_content_angle,
                                related_topics=safe_related_topics
                            )
                            
                            if insight:
                                # 캐시에 저장
                                st.session_state.hs_insight_cache[cache_key] = insight
                                st.session_state[show_insight_key] = True
                                st.markdown("### 📌 LG HS Strategic Content Insight")
                                st.markdown(insight)
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
        
        st.markdown("---")


def render_category_section(category_key: str, topics: list):
    """
    카테고리 섹션을 렌더링
    
    Args:
        category_key: 카테고리 키 (예: "SPRING_RECIPES")
        topics: 해당 카테고리의 토픽 리스트
    """
    # 카테고리 이름을 더 읽기 쉽게 변환
    category_display = category_key.replace('_', ' ').title()
    
    # 카테고리 헤더
    st.markdown(f"### {category_display}")
    st.markdown("")
    
    # 토픽 카드 렌더링
    if topics:
        for idx, topic in enumerate(topics, start=1):
            render_topic_card(topic, idx, category_key)
    else:
        st.info("이 카테고리에 토픽이 없습니다.")


def render_master_topics():
    """Master Topics 탭 렌더링"""
    # 프로젝트 루트 경로
    project_root = Path(__file__).parent.parent.parent
    
    # JSON 파일 경로 (올바른 형식의 파일을 우선적으로 찾음)
    possible_paths = [
        project_root / "data" / "master_topics_final_kr_en_RICH_WHY.json",
        project_root / "master_topics_final_kr_en_RICH_WHY.json",
        # master_topics.json은 마크다운 문자열 형식이므로 제외
    ]
    
    # 파일 찾기
    json_path = None
    for path in possible_paths:
        if path.exists():
            json_path = str(path)
            break
    
    if not json_path:
        st.error("마스터 토픽 JSON 파일을 찾을 수 없습니다. 다음 경로를 확인해주세요:")
        for path in possible_paths:
            st.text(f"  - {path}")
        return
    
    # JSON 로드
    topics_data = load_master_topics(json_path)
    
    if topics_data is None:
        st.error("마스터 토픽 데이터를 로드할 수 없습니다.")
        return
    
    # 데이터 형식 검증: 각 카테고리가 리스트인지 확인
    if isinstance(topics_data, dict):
        for category_key, category_data in topics_data.items():
            if not isinstance(category_data, list):
                st.error(f"⚠️ '{category_key}' 카테고리의 데이터 형식이 올바르지 않습니다.")
                st.info("마스터 토픽 파일은 각 카테고리가 토픽 객체의 리스트여야 합니다.")
                st.info(f"현재 파일: {json_path}")
                return
    
    # 필터 Selectbox (라벨 제거, width 늘리기)
    filter_options = [
        "ALL",
        "SPRING_RECIPES",
        "REFRIGERATOR_ORGANIZATION",
        "VEGETABLE_PREP_HANDLING",
        "SPRING_KITCHEN_STYLING"
    ]
    
    # 필터를 전체 너비로 배치
    selected_category = st.selectbox(
        "",  # 라벨 제거
        options=filter_options,
        index=0,  # 기본값: "ALL"
        key="master_topics_filter"
    )
    
    st.markdown("")
    
    # 필터링된 카테고리 렌더링
    if selected_category == "ALL":
        # 모든 카테고리 표시
        for category_key in filter_options[1:]:  # "ALL" 제외
            if category_key in topics_data:
                render_category_section(category_key, topics_data[category_key])
                st.markdown("")
    else:
        # 선택된 카테고리만 표시
        if selected_category in topics_data:
            render_category_section(selected_category, topics_data[selected_category])
        else:
            st.warning(f"'{selected_category}' 카테고리에 데이터가 없습니다.")
