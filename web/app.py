"""
LG전자용 콘텐츠 인텔리전스 대시보드

목적: DB에 저장된 분석 결과를 조회하여 콘텐츠 기획에 활용
- 데이터 수집/분석/LLM 호출 없음 (읽기 전용)
- 데이터 없을 경우에도 앱이 깨지지 않음
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from db_queries import (
    get_executive_overview,
    get_reddit_posts,
    get_serp_aio,
    get_clusters_with_trends,
    get_cluster_timeseries,
    get_cluster_representative_posts,
    get_master_topics,
    get_serp_aio_audit,
    check_lg_domain,
    parse_cited_sources
)

# 페이지 설정
st.set_page_config(
    page_title="LG Content Intelligence Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .lg-badge {
        background-color: #A50034;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
    }
    .opportunity-high {
        background-color: #FFE5E5;
        padding: 8px;
        border-radius: 4px;
        border-left: 4px solid #A50034;
    }
    .opportunity-medium {
        background-color: #FFF4E5;
        padding: 8px;
        border-radius: 4px;
        border-left: 4px solid #FFA500;
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.title("🏠 LG Content Intelligence Dashboard")
st.markdown("**목적**: Reddit, SERP AI Overview, GSC 데이터 기반 콘텐츠 주제 발굴 및 기획")
st.markdown("---")

# 탭 구성
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive Overview",
    "📥 Raw Data Explorer",
    "🔍 Cluster & Trend Explorer",
    "💡 Master Topic Explorer",
    "🔎 SERP AIO Audit",
    "📈 Opportunity Matrix"
])

# ============================================================================
# TAB 0: Executive Overview
# ============================================================================
with tab0:
    st.header("📊 Executive Overview")
    st.markdown("**목적**: 임원/마케팅 리더용 1페이지 요약")
    st.markdown("---")
    
    # DATABASE_URL 확인
    import os
    database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("RAILWAY_DATABASE_URL") or 
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRES_PRIVATE_URL")
    )
    if not database_url:
        st.warning("⚠️ DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        st.info("""
        Railway에서 PostgreSQL 서비스를 추가하고 연결하세요:
        1. Railway 대시보드 → 프로젝트 → "New" → "Database" → "PostgreSQL"
        2. PostgreSQL 서비스가 생성되면 DATABASE_URL이 자동으로 설정됩니다
        3. Streamlit 서비스의 "Variables" 탭에서 DATABASE_URL 확인
        """)
        # st.stop() 제거 - 대시보드가 로드되도록 함
    
    try:
        overview = get_executive_overview()
        
        # 주요 지표
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Master Topics", overview.get("total_topics", 0))
        
        with col2:
            seasonal = overview.get("seasonal_count", 0)
            evergreen = overview.get("evergreen_count", 0)
            total_cat = seasonal + evergreen
            if total_cat > 0:
                seasonal_pct = (seasonal / total_cat) * 100
                st.metric("Seasonal Topics", f"{seasonal} ({seasonal_pct:.1f}%)")
            else:
                st.metric("Seasonal Topics", "N/A")
        
        with col3:
            aio_avail = overview.get("aio_available", 0)
            aio_not = overview.get("aio_not_available", 0)
            aio_total = aio_avail + aio_not
            if aio_total > 0:
                aio_pct = (aio_avail / aio_total) * 100
                st.metric("AIO Available", f"{aio_avail} ({aio_pct:.1f}%)")
            else:
                st.metric("AIO Available", "N/A")
        
        with col4:
            lg_cited = overview.get("lg_cited_count", 0)
            total_topics = overview.get("total_topics", 0)
            if total_topics > 0:
                lg_pct = (lg_cited / total_topics) * 100
                st.metric("LG Cited Topics", f"{lg_cited} ({lg_pct:.1f}%)")
            else:
                st.metric("LG Cited Topics", "N/A")
        
        st.markdown("---")
        
        # 우선 검토 Master Topic Top 5
        st.subheader("🎯 우선 검토 Master Topic Top 5")
        top_topics = overview.get("top_topics", [])
        
        if top_topics:
            for i, (cluster_id, title, category, score, evidence_score) in enumerate(top_topics, 1):
                with st.expander(f"{i}. {title or 'Untitled'} ({category or 'Unknown'})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Cluster ID**: {cluster_id}")
                        st.write(f"**Category**: {category or 'Unknown'}")
                    with col2:
                        st.write(f"**Score**: {score:.2f}" if score else "**Score**: N/A")
                        st.write(f"**Evidence Strength**: {evidence_score or 'N/A'}")
        else:
            st.info("No master topics available")
    
    except Exception as e:
        st.error(f"Error loading executive overview: {e}")
        st.info("No data available")

# ============================================================================
# TAB 1: Raw Data Explorer
# ============================================================================
with tab1:
    st.header("📥 Raw Data Explorer")
    st.markdown("**목적**: 원천 데이터 검증 및 탐색")
    st.markdown("---")
    
    data_type = st.radio("Data Type", ["Reddit Posts", "SERP AI Overview"], horizontal=True)
    
    if data_type == "Reddit Posts":
        st.subheader("Reddit Posts")
        
        keyword_filter = st.text_input("Filter by keyword (optional)", "")
        
        try:
            df = get_reddit_posts(keyword_filter if keyword_filter else None)
            
            if len(df) > 0:
                st.write(f"**Total posts**: {len(df)}")
                
                # 필터링 옵션
                col1, col2 = st.columns(2)
                with col1:
                    min_upvotes = st.number_input("Min upvotes", min_value=0, value=0)
                with col2:
                    sort_by = st.selectbox("Sort by", ["upvotes", "num_comments", "created_at"])
                
                # 필터링 및 정렬
                filtered_df = df[df['upvotes'] >= min_upvotes].copy()
                if sort_by:
                    filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)
                
                # 테이블 표시
                display_df = filtered_df[['keyword', 'title', 'upvotes', 'num_comments', 'created_at', 'permalink']].copy()
                display_df['permalink'] = display_df['permalink'].apply(
                    lambda x: f"[Link](https://reddit.com{x})" if x else "N/A"
                )
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # CSV 다운로드
                csv = filtered_df.to_csv(index=False)
                st.download_button("Download CSV", csv, "reddit_posts.csv", "text/csv")
            else:
                st.info("No Reddit posts available")
        
        except Exception as e:
            st.error(f"Error loading Reddit posts: {e}")
            st.info("No data available")
    
    else:  # SERP AI Overview
        st.subheader("SERP AI Overview")
        
        try:
            df = get_serp_aio()
            
            if len(df) > 0:
                st.write(f"**Total queries**: {len(df)}")
                
                # AIO Status 필터
                status_filter = st.multiselect(
                    "Filter by AIO Status",
                    ["AVAILABLE", "NOT_AVAILABLE", "ERROR"],
                    default=["AVAILABLE", "NOT_AVAILABLE", "ERROR"]
                )
                
                if status_filter:
                    filtered_df = df[df['aio_status'].isin(status_filter)].copy()
                else:
                    filtered_df = df.copy()
                
                # 테이블 표시
                display_df = filtered_df[['query', 'aio_status', 'snapshot_at', 'locale']].copy()
                
                for idx, row in filtered_df.iterrows():
                    with st.expander(f"{row['query']} - {row['aio_status']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Status**: {row['aio_status']}")
                            st.write(f"**Snapshot**: {row['snapshot_at']}")
                            st.write(f"**Locale**: {row['locale']}")
                        
                        with col2:
                            if row['aio_status'] == 'AVAILABLE' and row['aio_text']:
                                st.write("**AI Overview Text**:")
                                st.text_area("", row['aio_text'], height=200, key=f"aio_{idx}", disabled=True)
                                
                                # Cited sources
                                sources = parse_cited_sources(row['cited_sources_json'])
                                if sources:
                                    st.write(f"**Cited Sources**: {len(sources)}")
                                    for source in sources[:5]:
                                        lg_badge = " 🏠 LG" if source['is_lg'] else ""
                                        st.write(f"- [{source['title'] or source['domain']}]({source['url']}){lg_badge}")
                            else:
                                st.warning("NOT AVAILABLE - No AI Overview for this query")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # CSV 다운로드
                csv = filtered_df.to_csv(index=False)
                st.download_button("Download CSV", csv, "serp_aio.csv", "text/csv")
            else:
                st.info("No SERP AI Overview data available")
        
        except Exception as e:
            st.error(f"Error loading SERP AIO: {e}")
            st.info("No data available")

# ============================================================================
# TAB 2: Cluster & Trend Explorer
# ============================================================================
with tab2:
    st.header("🔍 Cluster & Trend Explorer")
    st.markdown("**목적**: 클러스터 구조 및 트렌드 분석")
    st.markdown("---")
    
    try:
        clusters_df = get_clusters_with_trends()
        
        if len(clusters_df) > 0:
            st.write(f"**Total clusters**: {len(clusters_df)}")
            
            # 클러스터 선택
            cluster_options = clusters_df.apply(
                lambda row: f"Cluster {row['cluster_id']} ({row['category'] or 'Unknown'}, size={row['size']})",
                axis=1
            ).tolist()
            
            selected_cluster_idx = st.selectbox("Select Cluster", range(len(cluster_options)), format_func=lambda x: cluster_options[x])
            selected_cluster_id = clusters_df.iloc[selected_cluster_idx]['cluster_id']
            selected_category = clusters_df.iloc[selected_cluster_idx]['category']
            
            st.markdown("---")
            
            # 클러스터 상세 정보
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Cluster ID", selected_cluster_id)
            with col2:
                st.metric("Size", clusters_df.iloc[selected_cluster_idx]['size'])
            with col3:
                st.metric("Representative Samples", clusters_df.iloc[selected_cluster_idx]['representative_count'])
            
            # 시계열 차트
            st.subheader("📈 Monthly Trend")
            try:
                timeseries_df = get_cluster_timeseries(selected_cluster_id)
                
                if len(timeseries_df) > 0:
                    # 차트
                    fig = px.line(
                        timeseries_df,
                        x='month',
                        y='reddit_weighted_score',
                        title=f"Cluster {selected_cluster_id} - Reddit Weighted Score Trend",
                        markers=True
                    )
                    fig.update_layout(xaxis_title="Month", yaxis_title="Weighted Score")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 테이블
                    st.dataframe(timeseries_df, use_container_width=True, hide_index=True)
                    
                    # 시즌성 해석
                    is_seasonal = selected_category in ['SPRING_RECIPES', 'SPRING_KITCHEN_STYLING']
                    if is_seasonal:
                        st.info("🌱 **Seasonal Category**: This cluster is interpreted with spring seasonality adjustment. "
                               "Trend analysis compares current spring performance against historical spring baseline.")
                    else:
                        st.info("📊 **Evergreen Category**: This cluster is interpreted with absolute growth metrics. "
                               "Spring season increases may indicate lifestyle reset/organization needs.")
                else:
                    st.info("No timeseries data available for this cluster")
            
            except Exception as e:
                st.warning(f"Error loading timeseries: {e}")
            
            # 대표 포스트
            st.subheader("📝 Representative Posts")
            try:
                rep_posts_df = get_cluster_representative_posts(selected_cluster_id)
                
                if len(rep_posts_df) > 0:
                    for idx, row in rep_posts_df.iterrows():
                        with st.expander(f"{row['title']} (↑{row['upvotes']}, 💬{row['num_comments']})"):
                            st.write(f"**Keyword**: {row['keyword']}")
                            st.write(f"**Created**: {row['created_at']}")
                            st.write(f"**Link**: [Reddit Post](https://reddit.com{row['permalink']})")
                            if row['body']:
                                st.text_area("Body", row['body'], height=100, key=f"body_{idx}", disabled=True)
                else:
                    st.info("No representative posts available")
            
            except Exception as e:
                st.warning(f"Error loading representative posts: {e}")
        
        else:
            st.info("No clusters available")
    
    except Exception as e:
        st.error(f"Error loading clusters: {e}")
        st.info("No data available")

# ============================================================================
# TAB 3: Master Topic Explorer (핵심)
# ============================================================================
with tab3:
    st.header("💡 Master Topic Explorer")
    st.markdown("**목적**: 콘텐츠 기획에 바로 활용 가능한 Master Topic 탐색")
    st.markdown("---")
    
    # 필터
    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox(
            "Category",
            ["All", "SPRING_RECIPES", "SPRING_KITCHEN_STYLING", 
             "REFRIGERATOR_ORGANIZATION", "VEGETABLE_PREP_HANDLING"]
        )
    with col2:
        aio_filter = st.selectbox(
            "AIO Status",
            ["All", "AVAILABLE", "NOT_AVAILABLE"]
        )
    with col3:
        lg_filter = st.selectbox(
            "LG Citation",
            ["All", "Yes", "No"]
        )
    
    try:
        category = category_filter if category_filter != "All" else None
        topics_df = get_master_topics(category_filter=category)
        
        if len(topics_df) > 0:
            st.write(f"**Total topics**: {len(topics_df)}")
            
            # 카드 리스트
            for idx, row in topics_df.iterrows():
                with st.expander(f"📌 {row['topic_title']} ({row['category']})"):
                    # 헤더 메트릭
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Cluster ID", row['cluster_id'])
                    with col2:
                        st.metric("Cluster Size", row['cluster_size'])
                    with col3:
                        score = row['score'] if pd.notna(row['score']) else None
                        st.metric("Priority Score", f"{score:.2f}" if score else "N/A")
                    with col4:
                        evidence_score = row['evidence_score'] if pd.notna(row['evidence_score']) else None
                        st.metric("Evidence Strength", evidence_score or "N/A")
                    
                    st.markdown("---")
                    
                    # Primary Question
                    st.subheader("❓ Primary Question")
                    st.write(row['primary_question'] or "N/A")
                    
                    # Related Questions
                    st.subheader("💭 Related Questions")
                    related_questions = row['related_questions_json']
                    if related_questions:
                        if isinstance(related_questions, str):
                            try:
                                related_questions = json.loads(related_questions)
                            except:
                                pass
                        if isinstance(related_questions, list):
                            for q in related_questions:
                                st.write(f"- {q}")
                        else:
                            st.info("Related questions not available")
                    else:
                        st.info("Related questions not available")
                    
                    # Why Now
                    st.subheader("⏰ Why Now")
                    why_now = row['why_now_json']
                    if why_now:
                        if isinstance(why_now, str):
                            try:
                                why_now = json.loads(why_now)
                            except:
                                pass
                        if isinstance(why_now, dict):
                            st.write(f"**Trend Summary**: {why_now.get('trend_summary', 'N/A')}")
                            st.write(f"**Drivers**: {', '.join(why_now.get('drivers', []))}")
                            st.write(f"**Expected Impact**: {why_now.get('expected_impact', 'N/A')}")
                    else:
                        st.info("Why Now information not available")
                    
                    # Blog Angle
                    st.subheader("📝 Blog Angle")
                    st.write(row['blog_angle'] or "N/A")
                    
                    # Social Angle
                    st.subheader("📱 Social Angle")
                    st.write(row['social_angle'] or "N/A")
                    
                    # Evidence Pack
                    st.subheader("📦 Evidence Pack")
                    evidence = row['evidence_pack_json']
                    if evidence:
                        if isinstance(evidence, str):
                            try:
                                evidence = json.loads(evidence)
                            except:
                                pass
                        if isinstance(evidence, dict):
                            # Reddit
                            if evidence.get('reddit_posts'):
                                st.write("**Reddit Posts**:")
                                for post in evidence['reddit_posts'][:3]:
                                    st.write(f"- {post.get('title', 'N/A')} (↑{post.get('upvotes', 0)})")
                            
                            # SERP AIO
                            serp_aio = evidence.get('serp_aio')
                            if serp_aio and serp_aio != "NOT_AVAILABLE":
                                st.write("**SERP AI Overview**:")
                                st.write(serp_aio.get('aio_summary', 'N/A'))
                            else:
                                st.write("**SERP AI Overview**: NOT AVAILABLE")
                            
                            # GSC
                            gsc = evidence.get('gsc_data')
                            if gsc and gsc != "not available":
                                st.write("**GSC Data**:")
                                if isinstance(gsc, dict) and gsc.get('top_queries'):
                                    st.write(f"Total queries: {len(gsc['top_queries'])}")
                                else:
                                    st.write("Available")
                            else:
                                st.write("**GSC Data**: not available")
                    else:
                        st.info("Evidence pack not available")
                    
                    # CSV Export
                    st.markdown("---")
                    topic_data = {
                        'cluster_id': [row['cluster_id']],
                        'topic_title': [row['topic_title']],
                        'category': [row['category']],
                        'primary_question': [row['primary_question']],
                        'blog_angle': [row['blog_angle']],
                        'social_angle': [row['social_angle']]
                    }
                    topic_df = pd.DataFrame(topic_data)
                    csv = topic_df.to_csv(index=False)
                    st.download_button(
                        f"Download Topic {row['cluster_id']} CSV",
                        csv,
                        f"topic_{row['cluster_id']}.csv",
                        "text/csv",
                        key=f"download_{idx}"
                    )
        else:
            st.info("No master topics available")
    
    except Exception as e:
        st.error(f"Error loading master topics: {e}")
        st.info("No data available")

# ============================================================================
# TAB 4: SERP AI Overview Audit (LG 핵심 Audit)
# ============================================================================
with tab4:
    st.header("🔎 SERP AI Overview Audit")
    st.markdown("**목적**: Google AI Overview 인용 출처 감사 및 LG 도메인 인용 여부 확인")
    st.markdown("---")
    
    try:
        audit_df = get_serp_aio_audit()
        
        if len(audit_df) > 0:
            st.write(f"**Total AIO queries**: {len(audit_df)}")
            
            # AIO Query 테이블
            st.subheader("📋 AIO Query Summary")
            
            summary_data = []
            for idx, row in audit_df.iterrows():
                sources = parse_cited_sources(row['cited_sources_json'])
                lg_cited = any(s['is_lg'] for s in sources)
                
                summary_data.append({
                    'query': row['query'],
                    'master_topic': row['master_topic'] or 'N/A',
                    'aio_status': row['aio_status'],
                    'cited_urls_count': len(sources),
                    'lg_cited': 'Yes' if lg_cited else 'No'
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # AIO 상세
            st.subheader("📄 AIO Details")
            
            for idx, row in audit_df.iterrows():
                with st.expander(f"{row['query']} - {row['aio_status']}"):
                    # AIO 텍스트
                    if row['aio_status'] == 'AVAILABLE' and row['aio_text']:
                        st.write("**AI Overview Text**:")
                        st.text_area("", row['aio_text'], height=200, key=f"audit_aio_{idx}", disabled=True)
                    else:
                        st.warning("NOT AVAILABLE - No AI Overview for this query")
                    
                    # 인용 URL 리스트
                    sources = parse_cited_sources(row['cited_sources_json'])
                    if sources:
                        st.write(f"**Cited Sources**: {len(sources)}")
                        
                        lg_sources = [s for s in sources if s['is_lg']]
                        non_lg_sources = [s for s in sources if not s['is_lg']]
                        
                        if lg_sources:
                            st.success(f"🏠 **LG Cited**: {len(lg_sources)} sources")
                            for source in lg_sources:
                                st.write(f"- [{source['title'] or source['domain']}]({source['url']}) 🏠")
                        
                        if non_lg_sources:
                            st.write(f"**Other Sources**: {len(non_lg_sources)}")
                            for source in non_lg_sources[:10]:  # Top 10
                                st.write(f"- [{source['title'] or source['domain']}]({source['url']})")
                    else:
                        st.info("No cited sources available")
            
            st.markdown("---")
            
            # 도메인 점유 분석
            st.subheader("📊 Domain Share Analysis")
            
            all_sources = []
            for idx, row in audit_df.iterrows():
                sources = parse_cited_sources(row['cited_sources_json'])
                all_sources.extend(sources)
            
            if all_sources:
                # 도메인별 집계
                domain_counts = {}
                lg_domain_counts = {}
                
                for source in all_sources:
                    domain = source['domain']
                    if domain:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                        if source['is_lg']:
                            lg_domain_counts[domain] = lg_domain_counts.get(domain, 0) + 1
                
                # 상위 도메인 테이블
                domain_df = pd.DataFrame([
                    {
                        'domain': domain,
                        'citation_count': count,
                        'is_lg': 'Yes' if domain in lg_domain_counts else 'No'
                    }
                    for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
                ]).head(20)
                
                st.dataframe(domain_df, use_container_width=True, hide_index=True)
                
                # LG 도메인 점유율
                lg_total = sum(lg_domain_counts.values())
                total_citations = len(all_sources)
                lg_pct = (lg_total / total_citations * 100) if total_citations > 0 else 0
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("LG Citations", f"{lg_total} / {total_citations}")
                with col2:
                    st.metric("LG Share", f"{lg_pct:.1f}%")
                
                # 해석 배지
                st.markdown("---")
                st.subheader("🎯 Opportunity Assessment")
                
                for idx, row in audit_df.iterrows():
                    sources = parse_cited_sources(row['cited_sources_json'])
                    lg_cited = any(s['is_lg'] for s in sources)
                    
                    if row['aio_status'] == 'AVAILABLE' and not lg_cited:
                        st.markdown(f"<div class='opportunity-high'>"
                                  f"<strong>최우선 개선 기회</strong>: {row['query']} - AIO 있음 + LG 미인용</div>",
                                  unsafe_allow_html=True)
                    elif row['aio_status'] == 'NOT_AVAILABLE':
                        st.markdown(f"<div class='opportunity-medium'>"
                                  f"<strong>선점 기회</strong>: {row['query']} - AIO 없음</div>",
                                  unsafe_allow_html=True)
                    elif row['aio_status'] == 'AVAILABLE' and lg_cited:
                        st.success(f"✅ **방어/확장**: {row['query']} - AIO 있음 + LG 인용됨")
            else:
                st.info("No cited sources to analyze")
        else:
            st.info("No SERP AIO audit data available")
    
    except Exception as e:
        st.error(f"Error loading SERP AIO audit: {e}")
        st.info("No data available")

# ============================================================================
# TAB 5: Opportunity Matrix
# ============================================================================
with tab5:
    st.header("📈 Opportunity Matrix")
    st.markdown("**목적**: Reddit Engagement vs SERP AIO Presence 기반 기회 매트릭스")
    st.markdown("---")
    
    try:
        # Master Topics 데이터 조회
        topics_df = get_master_topics()
        
        if len(topics_df) > 0:
            # 매트릭스 데이터 준비
            matrix_data = []
            
            for idx, row in topics_df.iterrows():
                cluster_id = row['cluster_id']
                
                # Reddit Engagement (최근 3개월 가중 점수)
                try:
                    timeseries_df = get_cluster_timeseries(cluster_id)
                    if len(timeseries_df) > 0:
                        recent_scores = timeseries_df.head(3)['reddit_weighted_score'].tolist()
                        weights = [1.0, 0.7, 0.5]
                        reddit_engagement = sum(score * w for score, w in zip(recent_scores[:len(weights)], weights))
                    else:
                        reddit_engagement = 0.0
                except:
                    reddit_engagement = 0.0
                
                # SERP AIO Presence (0 or 1)
                try:
                    # 클러스터 키워드로 AIO 확인
                    aio_df = get_serp_aio()
                    cluster_keywords = [row['category']] if row['category'] else []
                    aio_presence = 0
                    if len(aio_df) > 0:
                        for aio_row in aio_df.itertuples():
                            if aio_row.aio_status == 'AVAILABLE':
                                # 간단한 매칭 (실제로는 더 정교한 로직 필요)
                                if any(kw.lower() in str(aio_row.query).lower() for kw in cluster_keywords):
                                    aio_presence = 1
                                    break
                except:
                    aio_presence = 0
                
                # LG Citation 여부
                lg_cited = False
                try:
                    evidence = row['evidence_pack_json']
                    if evidence:
                        if isinstance(evidence, str):
                            evidence = json.loads(evidence)
                        serp_aio = evidence.get('serp_aio')
                        if serp_aio and serp_aio != "NOT_AVAILABLE":
                            # Cited sources에서 LG 체크
                            sources = parse_cited_sources(serp_aio.get('cited_sources', []))
                            lg_cited = any(s['is_lg'] for s in sources)
                except:
                    pass
                
                matrix_data.append({
                    'cluster_id': cluster_id,
                    'topic_title': row['topic_title'],
                    'category': row['category'],
                    'reddit_engagement': reddit_engagement,
                    'aio_presence': aio_presence,
                    'lg_cited': lg_cited
                })
            
            matrix_df = pd.DataFrame(matrix_data)
            
            if len(matrix_df) > 0:
                # 2D Scatter Plot
                fig = px.scatter(
                    matrix_df,
                    x='reddit_engagement',
                    y='aio_presence',
                    color='lg_cited',
                    size='reddit_engagement',
                    hover_data=['topic_title', 'category'],
                    title="Opportunity Matrix: Reddit Engagement vs AIO Presence",
                    labels={
                        'reddit_engagement': 'Reddit Engagement (Weighted Score)',
                        'aio_presence': 'SERP AIO Presence (0=No, 1=Yes)',
                        'lg_cited': 'LG Cited'
                    },
                    color_discrete_map={True: '#A50034', False: '#999999'}
                )
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # 사분면 해석
                st.markdown("---")
                st.subheader("📊 Quadrant Interpretation")
                
                high_reddit_threshold = matrix_df['reddit_engagement'].quantile(0.5)
                
                q1 = matrix_df[(matrix_df['reddit_engagement'] >= high_reddit_threshold) & (matrix_df['aio_presence'] == 0)]
                q2 = matrix_df[(matrix_df['reddit_engagement'] >= high_reddit_threshold) & (matrix_df['aio_presence'] == 1) & (~matrix_df['lg_cited'])]
                q3 = matrix_df[(matrix_df['reddit_engagement'] < high_reddit_threshold) & (matrix_df['aio_presence'] == 1)]
                q4 = matrix_df[(matrix_df['reddit_engagement'] < high_reddit_threshold) & (matrix_df['aio_presence'] == 0)]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Q1: High Reddit / No AIO → 선점 기회**")
                    if len(q1) > 0:
                        st.write(f"{len(q1)} topics")
                        for _, row in q1.head(5).iterrows():
                            st.write(f"- {row['topic_title']}")
                    else:
                        st.info("No topics in this quadrant")
                    
                    st.markdown("**Q2: High Reddit / AIO + LG 미인용 → SEO/AIO 대응 최우선**")
                    if len(q2) > 0:
                        st.write(f"{len(q2)} topics")
                        for _, row in q2.head(5).iterrows():
                            st.write(f"- {row['topic_title']}")
                    else:
                        st.info("No topics in this quadrant")
                
                with col2:
                    st.markdown("**Q3: Low Reddit / AIO 있음 → 후순위**")
                    if len(q3) > 0:
                        st.write(f"{len(q3)} topics")
                        for _, row in q3.head(5).iterrows():
                            st.write(f"- {row['topic_title']}")
                    else:
                        st.info("No topics in this quadrant")
                    
                    st.markdown("**Q4: Low / Low → 보류**")
                    if len(q4) > 0:
                        st.write(f"{len(q4)} topics")
                        for _, row in q4.head(5).iterrows():
                            st.write(f"- {row['topic_title']}")
                    else:
                        st.info("No topics in this quadrant")
                
                # CSV 다운로드
                csv = matrix_df.to_csv(index=False)
                st.download_button("Download Matrix CSV", csv, "opportunity_matrix.csv", "text/csv")
            else:
                st.info("No matrix data available")
        else:
            st.info("No master topics available for matrix")
    
    except Exception as e:
        st.error(f"Error loading opportunity matrix: {e}")
        st.info("No data available")

# ============================================================================
# Footer
# ============================================================================
st.markdown("---")
st.markdown("**Note**: This dashboard is read-only. Data collection and analysis are performed separately via the pipeline.")
