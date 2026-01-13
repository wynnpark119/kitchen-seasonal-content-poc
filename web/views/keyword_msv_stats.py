"""
구글 검색 결과 뷰

구글 검색 결과 데이터를 표시
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from web.components import render_insight_card, render_card
from common.file_loader import load_json


def load_keyword_msv_data() -> Optional[Dict]:
    """키워드 MSV JSON 데이터 로드"""
    from common.path_utils import get_data_dir
    
    data = load_json("keyword_msv_table.json", required=False)
    
    if data is None:
        data_dir = get_data_dir()
        file_path = data_dir / "keyword_msv_table.json"
        st.warning("⚠️ 키워드 MSV 데이터 파일을 찾을 수 없습니다.")
        st.info(f"💡 파일 경로: `{file_path}`")
        st.info(f"💡 데이터 디렉토리: `{data_dir}`")
        st.info("💡 `scripts/convert_keyword_table_to_json.py`를 실행하여 데이터를 생성하세요.")
    
    return data


def render_keyword_msv_stats():
    """구글 검색 결과 탭 렌더링"""
    
    # 데이터 로드
    data = load_keyword_msv_data()
    if data is None:
        return
    
    # DataFrame 생성
    items = data.get('items', [])
    if not items:
        st.warning("⚠️ 키워드 데이터가 없습니다.")
        return
    
    df = pd.DataFrame(items)
    
    # 기본 정렬 (구글 검색량 내림차순)
    if 'msv_google_worldwide' in df.columns:
        df = df.sort_values(
            'msv_google_worldwide',
            ascending=False,
            na_position='last'
        )
    df = df.reset_index(drop=True)
    
    # KPI 카드 (3분할 레이아웃)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_keywords = len(df)
        render_insight_card(
            title="전체 키워드 수",
            value=f"{total_keywords:,}개",
            description="분석 대상 키워드 총계",
            color="#2196F3"
        )
    
    with col2:
        aio_count = df['aio'].sum() if 'aio' in df.columns else 0
        aio_rate = (aio_count / total_keywords * 100) if total_keywords > 0 else 0
        render_insight_card(
            title="AIO 트리거 키워드",
            value=f"{aio_count:,}개",
            description=f"전체의 {aio_rate:.1f}%",
            color="#FF9800"
        )
    
    with col3:
        # 상위 키워드 Top 3
        if 'msv_google_worldwide' in df.columns:
            top_msv = df.nlargest(3, 'msv_google_worldwide')
            top_keywords_list = top_msv['keyword'].head(3).tolist()
            top_keywords_str = ", ".join(top_keywords_list)
            render_insight_card(
                title="상위 키워드",
                value="Top 3",
                description=top_keywords_str[:60] + "..." if len(top_keywords_str) > 60 else top_keywords_str,
                color="#4CAF50"
            )
        else:
            render_insight_card(
                title="상위 키워드",
                value="N/A",
                description="데이터 없음",
                color="#9E9E9E"
            )
    
    st.markdown("---")
    
    # 구글 검색 결과 섹션 - 보더 없이 깔끔하게 표시
    st.markdown(
        """
        <style>
        /* 구글 검색 결과 섹션 제목 */
        .google-results-section {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background: transparent !important;
            padding: 0 !important;
            margin-bottom: 0.25rem !important;
        }
        .google-search-card-title {
            margin: 0 0 0.25rem 0;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 600;
        }
        </style>
        <div class="google-results-section" id="google-results-section">
            <h4 class="google-search-card-title">구글 검색 결과</h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 구글 검색 결과 섹션의 보더 제거 (다른 섹션에 영향 없도록 구체적으로 타겟팅)
    st.markdown(
        """
        <style>
        /* 구글 검색 결과 섹션 이후의 모든 element-container 보더 제거 및 여백 조정 */
        /* 구글 검색 결과 제목 다음에 오는 요소들만 타겟팅 */
        #google-results-section ~ .element-container,
        #google-results-section ~ div,
        #google-results-section ~ div > div,
        #google-results-section ~ div > div > div {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        /* DataFrame 컨테이너의 상단 여백 제거 */
        #google-results-section ~ div .element-container:has([data-testid="stDataFrame"]),
        #google-results-section ~ div > div:has([data-testid="stDataFrame"]) {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        /* DataFrame 관련 모든 보더 제거 */
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] * {
            border: none !important;
            outline: none !important;
        }
        /* Streamlit의 기본 컨테이너 보더 제거 (구글 검색 결과 섹션 관련만) */
        .main .block-container > div:has([data-testid="stDataFrame"]) {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 표시용 DataFrame 준비 (remark는 길면 줄임)
    display_df = df.copy()
    
    # 숫자 포맷팅
    if 'msv_google_worldwide' in display_df.columns:
        display_df['msv_google_worldwide'] = display_df['msv_google_worldwide'].apply(
            lambda x: f"{x:,}" if pd.notna(x) and x is not None else "-"
        )
    
    if 'msv_perplexity' in display_df.columns:
        display_df['msv_perplexity'] = display_df['msv_perplexity'].apply(
            lambda x: f"{x:,}" if pd.notna(x) and x is not None else "-"
        )
    
    # AIO 표시
    if 'aio' in display_df.columns:
        display_df['aio'] = display_df['aio'].apply(lambda x: "O" if x else "")
    
    # 컬럼 선택 및 순서 지정 (비고 제외)
    columns_to_show = [
        'major_category',
        'minor_category',
        'keyword',
        'msv_google_worldwide',
        'msv_perplexity',
        'aio'
    ]
    
    # 컬럼명 한글화 (MSV 용어 제거)
    display_df_renamed = display_df[columns_to_show].rename(columns={
        'major_category': '대분류',
        'minor_category': '중분류',
        'keyword': '키워드',
        'msv_google_worldwide': '구글 검색량',
        'msv_perplexity': 'Perplexity 검색량',
        'aio': 'AIO'
    })
    
    # 테이블 표시
    st.dataframe(
        display_df_renamed,
        use_container_width=True,
        hide_index=True
    )
    
    # 인사이트 (expander)
    if len(df) > 0 and 'remark' in df.columns:
        remarks_with_content = df[
            df['remark'].notna() & 
            (df['remark'].astype(str).str.strip() != '')
        ]
        if len(remarks_with_content) > 0:
            with st.expander("인사이트", expanded=False):
                for idx, row in remarks_with_content.iterrows():
                    remark_text = str(row['remark']).strip()
                    if remark_text:
                        # 여러 줄 텍스트를 그대로 표시
                        st.markdown(f"**{row['keyword']}**")
                        st.markdown(remark_text)
                        st.markdown("---")
    
    # 데이터 소스 정보
    st.caption(f"데이터 생성일: {data.get('generated_at', 'N/A')} | 출처: {data.get('source', 'N/A')}")
