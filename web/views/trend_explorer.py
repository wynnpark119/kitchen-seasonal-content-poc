"""
Trend Explorer 뷰

SERP AI Overview / Trend Explorer 표시
"""
import streamlit as st
import pandas as pd

from services.serp_service import get_serp_service
from web.db_queries import parse_cited_sources
from web.components import render_insight_card, render_card


def classify_query_category(query: str) -> str:
    """
    쿼리를 4개 카테고리로 분류
    
    Returns:
        'SPRING_RECIPES', 'SPRING_KITCHEN_STYLING', 'REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING', 'OTHER'
    """
    query_lower = query.lower()
    
    # SPRING_RECIPES: recipe, meal, dinner, cook, food 관련
    if any(term in query_lower for term in ['recipe', 'meal', 'dinner', 'cook', 'food', 'dish', 'cuisine']):
        if any(term in query_lower for term in ['spring', 'seasonal', 'light', 'healthy']):
            return 'SPRING_RECIPES'
    
    # SPRING_KITCHEN_STYLING: decor, styling, design, refresh, atmosphere 관련
    if any(term in query_lower for term in ['decor', 'styling', 'style', 'design', 'refresh', 'atmosphere', 'aesthetic', 'table setting', 'interior']):
        if any(term in query_lower for term in ['kitchen', 'spring', 'seasonal']):
            return 'SPRING_KITCHEN_STYLING'
    
    # REFRIGERATOR_ORGANIZATION: refrigerator, fridge, organization 관련
    if any(term in query_lower for term in ['refrigerator', 'fridge', 'organization', 'organize', 'storage', 'organizing']):
        return 'REFRIGERATOR_ORGANIZATION'
    
    # VEGETABLE_PREP_HANDLING: vegetable, prep, wash, store, handling 관련
    if any(term in query_lower for term in ['vegetable', 'prep', 'wash', 'store', 'handling', 'cleaning', 'fresh']):
        if any(term in query_lower for term in ['vegetable', 'produce', 'greens']):
            return 'VEGETABLE_PREP_HANDLING'
    
    # 기본값: OTHER
    return 'OTHER'


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
        
        # 전체 게시물에서 채널 분포 집계
        total_lg_owned = 0
        total_competitor = 0
        total_earned_media = 0
        total_other = 0
        
        for _, row in filtered_df.iterrows():
            sources = parse_cited_sources(row.get('cited_sources_json'))
            if sources:
                for source in sources:
                    channel_type = source.get('channel_type', 'other')
                    if channel_type == 'lg_owned':
                        total_lg_owned += 1
                    elif channel_type == 'competitor':
                        total_competitor += 1
                    elif channel_type == 'earned_media':
                        total_earned_media += 1
                    else:
                        total_other += 1
        
        total_sources = total_lg_owned + total_competitor + total_earned_media + total_other
        
        # 채널 분포 통계 카드 (4분할 레이아웃)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            lg_rate = (total_lg_owned / total_sources * 100) if total_sources > 0 else 0
            render_insight_card(
                title="LG Owned",
                value=f"{total_lg_owned:,}개",
                description=f"전체의 {lg_rate:.1f}%" if total_sources > 0 else "데이터 없음",
                color="#2196F3"
            )
        with col2:
            competitor_rate = (total_competitor / total_sources * 100) if total_sources > 0 else 0
            render_insight_card(
                title="Competitor",
                value=f"{total_competitor:,}개",
                description=f"전체의 {competitor_rate:.1f}%" if total_sources > 0 else "데이터 없음",
                color="#FF9800"
            )
        with col3:
            earned_rate = (total_earned_media / total_sources * 100) if total_sources > 0 else 0
            render_insight_card(
                title="Earned Media",
                value=f"{total_earned_media:,}개",
                description=f"전체의 {earned_rate:.1f}%" if total_sources > 0 else "데이터 없음",
                color="#4CAF50"
            )
        with col4:
            other_rate = (total_other / total_sources * 100) if total_sources > 0 else 0
            render_insight_card(
                title="Other",
                value=f"{total_other:,}개",
                description=f"전체의 {other_rate:.1f}%" if total_sources > 0 else "데이터 없음",
                color="#9E9E9E"
            )
        
        st.markdown("---")
        
        # 쿼리를 카테고리별로 분류
        filtered_df['category'] = filtered_df['query'].apply(classify_query_category)
        
        # 카테고리별로 그룹화
        categories = ['SPRING_RECIPES', 'SPRING_KITCHEN_STYLING', 'REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING']
        category_labels = {
            'SPRING_RECIPES': 'Spring Recipes',
            'SPRING_KITCHEN_STYLING': 'Spring Kitchen Styling',
            'REFRIGERATOR_ORGANIZATION': 'Refrigerator Organization',
            'VEGETABLE_PREP_HANDLING': 'Vegetable Prep & Handling'
        }
        
        # 각 카테고리에 해당하는 데이터만 필터링
        available_categories = []
        category_dataframes = {}
        
        for cat in categories:
            cat_df = filtered_df[filtered_df['category'] == cat]
            if len(cat_df) > 0:
                available_categories.append(cat)
                category_dataframes[cat] = cat_df
        
        # 탭 생성
        if available_categories:
            tab_labels = [category_labels[cat] for cat in available_categories]
            tabs = st.tabs(tab_labels)
            
            for tab, category in zip(tabs, available_categories):
                with tab:
                    cat_df = category_dataframes[category]
                    
                    # 전체 항목 표시 (페이지네이션 제거)
                    display_df = cat_df
                    
                    # 검색 결과 리스트
                    for list_idx, (df_idx, row) in enumerate(display_df.iterrows(), start=1):
                        # 번호와 쿼리 제목
                        expander_title = f"{list_idx}. {row['query']}"
                        
                        with st.expander(expander_title):
                            st.markdown(f"**탐색어**: `{row['query']}`")
                            
                            # AI Overview 텍스트
                            if row['aio_status'] == 'AVAILABLE' and row.get('aio_text'):
                                st.markdown("**AI Overview**")
                                st.caption(row['aio_text'])
                            
                            # 참고 URL 채널 분포 및 상세 정보
                            sources = parse_cited_sources(row.get('cited_sources_json'))
                            if sources:
                                # 채널 타입별로 분류
                                lg_sources = [s for s in sources if s.get('channel_type') == 'lg_owned']
                                competitor_sources = [s for s in sources if s.get('channel_type') == 'competitor']
                                earned_sources = [s for s in sources if s.get('channel_type') == 'earned_media']
                                other_sources = [s for s in sources if s.get('channel_type') == 'other']
                                
                                # 채널 분포 통계
                                st.markdown("**참고 URL 채널 분포**")
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
        else:
            st.info("카테고리별 데이터가 없습니다.")
        
    except Exception as e:
        st.error(f"Error loading trend explorer data: {e}")
        st.info("Not available")
