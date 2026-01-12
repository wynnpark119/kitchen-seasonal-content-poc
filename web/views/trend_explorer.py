"""
Trend Explorer 뷰

SERP AI Overview / Trend Explorer 표시
"""
import streamlit as st
import pandas as pd

from services.serp_service import get_serp_service
from web.db_queries import parse_cited_sources


def generate_channel_summary(lg_count: int, competitor_count: int, earned_count: int, other_count: int) -> str:
    """
    채널 분포를 기반으로 요약 문구 생성
    
    규칙:
    - Competitor ≥ 3 → "대응 필요"
    - Earned ≥ 5 & LG Owned = 0 → "콘텐츠 기회 영역"
    - LG Owned > 0 → "LG 채널 노출 확인"
    - Earned Media 비중 높음 → "브랜드 개입 여지 큰 주제"
    """
    total = lg_count + competitor_count + earned_count + other_count
    if total == 0:
        return ""
    
    summaries = []
    
    # 경쟁사 대응 필요
    if competitor_count >= 3:
        summaries.append("경쟁사 Owned 콘텐츠가 다수 노출되고 있어, 대응 필요(Action required) 주제로 분류됩니다.")
    
    # 콘텐츠 기회 영역
    if earned_count >= 5 and lg_count == 0:
        summaries.append("해당 탐색 키워드는 Earned Media 비중이 높아, 브랜드 개입 여지가 큰 주제로 판단됩니다.")
    
    # LG 채널 노출 확인
    if lg_count > 0:
        summaries.append(f"LG 채널이 {lg_count}개 노출되어 브랜드 인지도가 확인됩니다.")
    
    # Earned Media 비중이 높은 경우
    earned_ratio = earned_count / total if total > 0 else 0
    if earned_ratio >= 0.5 and earned_count >= 3:
        summaries.append("Earned Media 비중이 높아, 브랜드 개입 여지가 큰 주제로 판단됩니다.")
    
    # 기본 요약
    if not summaries:
        if competitor_count > 0:
            summaries.append("경쟁사 콘텐츠가 일부 노출되고 있습니다.")
        elif earned_count > 0:
            summaries.append("Earned Media 콘텐츠가 주로 노출되고 있습니다.")
        else:
            summaries.append("다양한 채널에서 콘텐츠가 노출되고 있습니다.")
    
    return " ".join(summaries)


def render_trend_explorer():
    """구글 AI 검색 결과 분석 탭 렌더링"""
    serp_service = get_serp_service()
    
    # 페이지네이션 상태 관리
    if 'aio_display_count' not in st.session_state:
        st.session_state.aio_display_count = 20
    
    try:
        serp_df = serp_service.get_all_serp_data()
        
        if serp_df is None or len(serp_df) == 0:
            st.warning("⚠️ 구글 AI 검색 결과 데이터가 없습니다.")
            st.info("데이터 수집이 완료되면 결과가 표시됩니다.")
            return
        
        # 통계 요약
        filtered_df = serp_df[serp_df['aio_status'].isin(['AVAILABLE', 'NOT_AVAILABLE'])].copy()
        
        if len(filtered_df) == 0:
            st.warning("⚠️ 필터링된 구글 AI 검색 결과가 없습니다.")
            st.info("AVAILABLE 또는 NOT_AVAILABLE 상태의 데이터가 없습니다.")
            return
        
        col1, col2, col3 = st.columns(3)
        
        total_queries = len(filtered_df)
        available_count = len(filtered_df[filtered_df['aio_status'] == 'AVAILABLE'])
        not_available_count = len(filtered_df[filtered_df['aio_status'] == 'NOT_AVAILABLE'])
        
        with col1:
            st.metric("Total Queries", total_queries)
        with col2:
            st.metric("Available", f"{available_count} ({available_count/total_queries*100:.1f}%)" if total_queries > 0 else "0")
        with col3:
            st.metric("Not Available", f"{not_available_count} ({not_available_count/total_queries*100:.1f}%)" if total_queries > 0 else "0")
        
        st.markdown("---")
        
        # 현재 표시할 항목 수
        display_count = min(st.session_state.aio_display_count, len(filtered_df))
        display_df = filtered_df.head(display_count)
        
        # 검색 결과 리스트 (번호와 태그 포함)
        for list_idx, (df_idx, row) in enumerate(display_df.iterrows(), start=1):
            # 번호와 쿼리 제목
            expander_title = f"{list_idx}. {row['query']}"
            if pd.notna(row.get('snapshot_at')):
                expander_title += f" ({row['snapshot_at']})"
            
            # 상태 태그와 함께 표시
            col_tag, col_title = st.columns([1, 9])
            with col_tag:
                if row['aio_status'] == 'AVAILABLE':
                    st.markdown(f"<span style='background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;'>Action required</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;'>Not Available</span>", unsafe_allow_html=True)
            with col_title:
                with st.expander(expander_title):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**🔍 Query**: `{row['query']}`")
                    with col2:
                        if pd.notna(row.get('snapshot_at')):
                            st.caption(f"📅 {row['snapshot_at']}")
                    
                    # AI Overview 텍스트 또는 검색 결과
                    if row['aio_status'] == 'AVAILABLE' and row.get('aio_text'):
                        st.markdown("**📄 AI Overview:**")
                        st.info(row['aio_text'])
                    elif row.get('source_table') == 'serp_results':
                        st.markdown("**📄 검색 결과:**")
                        sources = parse_cited_sources(row.get('cited_sources_json'))
                        if sources:
                            st.info(f"총 {len(sources)}개의 검색 결과가 있습니다.")
                    
                    # 참고 URL (채널 분류)
                    sources = parse_cited_sources(row.get('cited_sources_json'))
                    if sources:
                        st.markdown("**🔗 참고 URL:**")
                        
                        # 채널 타입별로 분류
                        lg_sources = [s for s in sources if s.get('channel_type') == 'lg_owned']
                        competitor_sources = [s for s in sources if s.get('channel_type') == 'competitor']
                        earned_sources = [s for s in sources if s.get('channel_type') == 'earned_media']
                        other_sources = [s for s in sources if s.get('channel_type') == 'other']
                        
                        # 채널 분포 통계
                        st.markdown("**📌 참고 URL 채널 분포**")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("LG Owned", len(lg_sources))
                        with col2:
                            st.metric("Competitor", len(competitor_sources))
                        with col3:
                            st.metric("Earned Media", len(earned_sources))
                        with col4:
                            st.metric("Other", len(other_sources))
                        
                        # 카테고리별 expander로 표시
                        if lg_sources:
                            with st.expander(f"🏠 LG Owned ({len(lg_sources)})", expanded=False):
                                for source in lg_sources:
                                    url = source.get('url', '#')
                                    title = source.get('title', source.get('domain', 'N/A'))
                                    snippet = source.get('snippet', '')
                                    # 새 탭에서 열리도록 HTML 링크 사용
                                    st.markdown(f"- **<a href='{url}' target='_blank'>{title}</a>** [LG Owned]", unsafe_allow_html=True)
                                    if snippet:
                                        st.caption(f"  {snippet[:150]}...")
                        
                        if competitor_sources:
                            with st.expander(f"⚔️ Competitor ({len(competitor_sources)})", expanded=False):
                                for source in competitor_sources:
                                    url = source.get('url', '#')
                                    title = source.get('title', source.get('domain', 'N/A'))
                                    snippet = source.get('snippet', '')
                                    st.markdown(f"- **<a href='{url}' target='_blank'>{title}</a>** [Competitor]", unsafe_allow_html=True)
                                    if snippet:
                                        st.caption(f"  {snippet[:150]}...")
                        
                        if earned_sources:
                            with st.expander(f"📰 Earned Media ({len(earned_sources)})", expanded=False):
                                for source in earned_sources:
                                    url = source.get('url', '#')
                                    title = source.get('title', source.get('domain', 'N/A'))
                                    snippet = source.get('snippet', '')
                                    st.markdown(f"- **<a href='{url}' target='_blank'>{title}</a>** [Earned]", unsafe_allow_html=True)
                                    if snippet:
                                        st.caption(f"  {snippet[:150]}...")
                        
                        if other_sources:
                            with st.expander(f"🔗 Other ({len(other_sources)})", expanded=False):
                                for source in other_sources:
                                    url = source.get('url', '#')
                                    title = source.get('title', source.get('domain', 'N/A'))
                                    snippet = source.get('snippet', '')
                                    st.markdown(f"- **<a href='{url}' target='_blank'>{title}</a>** [Other]", unsafe_allow_html=True)
                                    if snippet:
                                        st.caption(f"  {snippet[:150]}...")
                        
                        # 요약 문구 자동 생성
                        summary_text = generate_channel_summary(
                            len(lg_sources), 
                            len(competitor_sources), 
                            len(earned_sources), 
                            len(other_sources)
                        )
                        if summary_text:
                            st.info(f"💡 **LG전자 관점 요약**: {summary_text}")
        
        # More 버튼 (더 많은 항목 표시)
        st.markdown("---")
        if display_count < len(filtered_df):
            remaining_count = len(filtered_df) - display_count
            if st.button(f"More ({remaining_count}개 더 보기)", key="aio_more_button"):
                st.session_state.aio_display_count += 20
                st.rerun()
        else:
            st.info(f"전체 {len(filtered_df)}개 항목을 모두 표시했습니다.")
            # 리셋 버튼
            if st.button("처음부터 보기", key="aio_reset_button"):
                st.session_state.aio_display_count = 20
                st.rerun()
        
        # CSV 다운로드
        st.markdown("---")
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            "SERP 데이터 다운로드 (CSV)",
            csv,
            "serp_aio_data.csv",
            "text/csv",
            key="download_serp_csv"
        )
        
    except Exception as e:
        st.error(f"Error loading trend explorer data: {e}")
        st.info("Not available")
