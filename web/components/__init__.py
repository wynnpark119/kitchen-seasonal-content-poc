"""
공통 UI 컴포넌트

카드 기반 레이아웃과 재사용 가능한 UI 컴포넌트를 제공합니다.
"""
import streamlit as st

# 기존 components.py의 함수들
def render_card(title: str, content, border_color: str = "#3d3d3d", padding: int = 20):
    """
    카드 스타일의 컨테이너를 렌더링합니다. (다크 모드 최적화)
    
    Args:
        title: 카드 제목
        content: 카드 내용 (Streamlit 컴포넌트 또는 함수)
        border_color: 테두리 색상 (기본값: #3d3d3d - 다크 모드용)
        padding: 내부 여백 (기본값: 20)
    """
    # 카드 시작 스타일 (제목만)
    card_id = f"card-{hash(title)}"
    st.markdown(
        f"""
        <style>
        #{card_id} {{
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: {padding}px;
            margin-bottom: 15px;
            background-color: #262730;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        #{card_id} h4 {{
            margin-top: 0;
            margin-bottom: 12px;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 600;
        }}
        /* 카드 다음 요소들에 카드 스타일 연장 */
        #{card_id} ~ * {{
            border-left: 1px solid {border_color};
            border-right: 1px solid {border_color};
            border-bottom: 1px solid {border_color};
            border-radius: 0 0 8px 8px;
            padding: 0 {padding}px {padding}px {padding}px;
            margin-top: -{padding}px;
            margin-bottom: 15px;
            background-color: #262730;
        }}
        </style>
        <div id="{card_id}">
            <h4>{title}</h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 카드 내용 렌더링
    if callable(content):
        content()
    else:
        st.markdown(content)


def render_insight_card(title: str, value: str, description: str = "", color: str = "#4A9EFF"):
    """
    인사이트 카드를 렌더링합니다. (다크 모드 최적화)
    
    Args:
        title: 카드 제목
        value: 주요 값 (큰 폰트로 표시)
        description: 설명 텍스트
        color: 강조 색상 (기본값: #4A9EFF - 다크 모드용 밝은 파란색)
    """
    st.markdown(
        f"""
        <div style="
            border: 1px solid #3d3d3d;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            background-color: #262730;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        ">
            <div style="color: #888888; font-size: 0.85rem; margin-bottom: 6px; line-height: 1.4;">
                {title}
            </div>
            <div style="color: {color}; font-size: 1.75rem; font-weight: bold; margin-bottom: 6px; line-height: 1.2; flex-grow: 1; display: flex; align-items: center;">
                {value}
            </div>
            {f'<div style="color: #888888; font-size: 0.8rem; line-height: 1.4;">{description}</div>' if description else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_section_header(title: str, subtitle: str = ""):
    """
    섹션 헤더를 렌더링합니다.
    
    Args:
        title: 섹션 제목
        subtitle: 서브타이틀 (선택사항)
    """
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def render_two_column_layout(left_content, right_content, left_width: int = 1, right_width: int = 1):
    """
    2분할 레이아웃을 렌더링합니다.
    
    Args:
        left_content: 왼쪽 컬럼 내용 (함수 또는 Streamlit 컴포넌트)
        right_content: 오른쪽 컬럼 내용 (함수 또는 Streamlit 컴포넌트)
        left_width: 왼쪽 컬럼 너비 비율 (기본값: 1)
        right_width: 오른쪽 컬럼 너비 비율 (기본값: 1)
    """
    col1, col2 = st.columns([left_width, right_width])
    
    with col1:
        if callable(left_content):
            left_content()
        else:
            st.markdown(left_content)
    
    with col2:
        if callable(right_content):
            right_content()
        else:
            st.markdown(right_content)


def render_four_column_layout(contents, widths=None):
    """
    4분할 레이아웃을 렌더링합니다.
    
    Args:
        contents: 4개의 컬럼 내용 리스트 (함수 또는 Streamlit 컴포넌트)
        widths: 각 컬럼의 너비 비율 리스트 (기본값: [1, 1, 1, 1])
    """
    if widths is None:
        widths = [1, 1, 1, 1]
    
    cols = st.columns(widths)
    
    for i, (col, content) in enumerate(zip(cols, contents)):
        with col:
            if callable(content):
                content()
            else:
                st.markdown(content)

__all__ = [
    'render_card',
    'render_insight_card',
    'render_section_header',
    'render_two_column_layout',
    'render_four_column_layout',
]
