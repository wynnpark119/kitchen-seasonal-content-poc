"""
Trend Explorer 뷰

SERP AI Overview / Trend Explorer 표시
"""
import streamlit as st
import pandas as pd

from services.serp_service import get_serp_service
from web.db_queries import parse_cited_sources


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
                    st.markdown(f"<span style='background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;'>Available</span>", unsafe_allow_html=True)
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
                    
                    # 참고 URL
                    sources = parse_cited_sources(row.get('cited_sources_json'))
                    if sources:
                        st.markdown("**🔗 참고 URL:**")
                        
                        lg_sources = [s for s in sources if s.get('is_lg', False)]
                        non_lg_sources = [s for s in sources if not s.get('is_lg', False)]
                        
                        if lg_sources:
                            st.success(f"🏠 **LG 인용**: {len(lg_sources)}개")
                            for source in lg_sources:
                                url = source.get('url', '#')
                                title = source.get('title', source.get('domain', 'N/A'))
                                snippet = source.get('snippet', '')
                                st.markdown(f"- **[{title}]({url})** 🏠")
                                if snippet:
                                    st.caption(f"  {snippet[:150]}...")
                        
                        if non_lg_sources:
                            st.markdown(f"**기타 참고 URL**: {len(non_lg_sources)}개")
                            for source in non_lg_sources[:10]:
                                url = source.get('url', '#')
                                title = source.get('title', source.get('domain', 'N/A'))
                                snippet = source.get('snippet', '')
                                position = source.get('position', '')
                                st.markdown(f"- **[{title}]({url})** {f'(위치: {position})' if position else ''}")
                                if snippet:
                                    st.caption(f"  {snippet[:150]}...")
                            
                            if len(non_lg_sources) > 10:
                                st.caption(f"... 외 {len(non_lg_sources) - 10}개 더")
        
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
