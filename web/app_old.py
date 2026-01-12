"""
LG전자용 콘텐츠 인텔리전스 대시보드

목적: DB에 저장된 분석 결과를 조회하여 콘텐츠 기획에 활용
- GPT API를 실시간으로 호출하여 요약 생성
- 데이터 없을 경우에도 앱이 깨지지 않음
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    # dotenv가 없으면 .env 파일을 직접 읽기
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and not os.getenv(key):
                        os.environ[key] = value

from db_queries import (
    get_executive_overview,
    get_reddit_posts,
    get_serp_aio,
    get_cluster_representative_posts,
    get_master_topics,
    get_serp_aio_audit,
    check_lg_domain,
    parse_cited_sources,
    get_cluster_summary_from_db,
    get_cluster_gpt_summaries,
    get_clustering_results_from_db,
    get_reddit_clustering_for_master_topic,
    get_serp_questions_for_master_topic
)

from gpt_utils import (
    generate_cluster_summary,
    generate_master_topics
)

# 페이지 설정
st.set_page_config(
    page_title="LG전자 HS 마스터 아티클 대시보드",
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
st.title("🏠 LG전자 HS 마스터 아티클 대시보드")
st.markdown("---")

# 탭 구성
tab0, tab1, tab2, tab3 = st.tabs([
    "📊 Overview",
    "🎯 Clustering Results",
    "🔍 SERP AI Overview",
    "🎯 Master Topic"
])

# ============================================================================
# TAB 0: Overview
# ============================================================================
with tab0:
    st.header("📊 Overview")
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
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Master Topics", overview.get("total_topics", 0))
        
        with col2:
            seasonal = overview.get("seasonal_count", 0)
            evergreen = overview.get("evergreen_count", 0)
            total_cat = seasonal + evergreen
            if total_cat > 0:
                seasonal_pct = (seasonal / total_cat) * 100
                st.metric("Seasonal Topics", f"{seasonal} ({seasonal_pct:.1f}%)")
            elif overview.get("total_topics", 0) > 0:
                # 카테고리 정보는 없지만 토픽은 있는 경우
                st.metric("Seasonal Topics", f"{seasonal} (카테고리 정보 없음)")
            else:
                st.metric("Seasonal Topics", "0")
        
        with col3:
            aio_avail = overview.get("aio_available", 0)
            aio_not = overview.get("aio_not_available", 0)
            aio_error = overview.get("aio_error", 0)
            aio_total = aio_avail + aio_not + aio_error
            if aio_total > 0:
                aio_pct = (aio_avail / aio_total) * 100
                st.metric("AIO Available", f"{aio_avail} ({aio_pct:.1f}%)")
            else:
                st.metric("AIO Available", "0")
        
        with col4:
            lg_cited = overview.get("lg_cited_count", 0)
            total_topics = overview.get("total_topics", 0)
            if total_topics > 0:
                lg_pct = (lg_cited / total_topics) * 100
                st.metric("LG Cited Topics", f"{lg_cited} ({lg_pct:.1f}%)")
            else:
                st.metric("LG Cited Topics", "0")
        
        with col5:
            # SERP 쿼리 수
            try:
                serp_df = get_serp_aio()
                serp_total = len(serp_df) if len(serp_df) > 0 else 0
                st.metric("SERP Queries", serp_total)
            except:
                st.metric("SERP Queries", "N/A")
        
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
            
        # 마스터 토픽 목록 (GPT 결과 없어도 기본 정보 표시)
        st.markdown("---")
        st.subheader("💡 Master Topics")
        try:
            topics_df = get_master_topics()
            if len(topics_df) > 0:
                st.write(f"**Total topics**: {len(topics_df)}")
                for idx, row in topics_df.head(10).iterrows():
                    topic_title = row.get('topic_title') or f"Cluster {row.get('cluster_id', 'Unknown')}"
                    category = row.get('category') or 'Unknown'
                    with st.expander(f"📌 {topic_title} ({category})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Cluster ID**: {row.get('cluster_id', 'N/A')}")
                        with col2:
                            st.write(f"**Category**: {category}")
                        with col3:
                            st.write(f"**Cluster Size**: {row.get('cluster_size', 'N/A')}")
                        
                        # GPT 결과가 있으면 표시, 없으면 기본 정보만
                        if pd.notna(row.get('primary_question')) and row.get('primary_question'):
                            st.markdown("**❓ Primary Question**")
                            st.write(row['primary_question'])
                        else:
                            st.info("Primary Question: Not available")
                        
                        if pd.notna(row.get('blog_angle')) and row.get('blog_angle'):
                            st.markdown("**📝 Blog Angle**")
                            st.write(row['blog_angle'])
                        else:
                            st.info("Blog Angle: Not available")
            else:
                st.info("No master topics available")
        except Exception as e:
            st.warning(f"Error loading master topics: {e}")
            st.info("Master topics data not available")
    
    except Exception as e:
        st.error(f"Error loading executive overview: {e}")
        st.info("No data available")

# ============================================================================
# TAB 1: Clustering Results (DB에서 조회)
# ============================================================================
with tab1:
    st.header("🎯 Clustering Results")
    st.markdown("---")
    
    try:
        # DB에서 클러스터링 결과 조회
        clusters_df = get_clustering_results_from_db()
        
        if len(clusters_df) == 0:
            st.warning("⚠️ DB에서 클러스터링 결과를 찾을 수 없습니다.")
            st.info("데이터베이스에 클러스터링 데이터가 적재되었는지 확인하세요.")
            st.info("""
            확인 사항:
            1. 데이터베이스 연결 상태 확인
            2. clusters 테이블에 데이터가 있는지 확인
            3. cluster_assignments 테이블에 데이터가 있는지 확인
            """)
        
        if len(clusters_df) > 0:
            # 클러스터 목록
            st.subheader("🔍 클러스터 정보")
            
            categories = clusters_df['topic_category'].dropna().unique()
            
            # 카테고리 선택
            available_categories = sorted([cat for cat in categories if pd.notna(cat)])
            if available_categories:
                selected_category = st.selectbox(
                    "카테고리 선택",
                    ["All"] + available_categories,
                    key="cluster_category_filter"
                )
                
                # 필터링
                if selected_category == "All":
                    # All 선택 시 topic_category가 None인 것들은 제외하거나 별도로 표시
                    filtered_df = clusters_df[clusters_df['topic_category'].notna()]
                    if len(clusters_df) > len(filtered_df):
                        num_without_category = len(clusters_df) - len(filtered_df)
                        st.info(f"ℹ️ topic_category가 없는 클러스터 {num_without_category}개는 제외되었습니다.")
                else:
                    filtered_df = clusters_df[clusters_df['topic_category'] == selected_category]
                
                st.write(f"**표시되는 클러스터**: {len(filtered_df)}개")
                
                st.markdown("---")
                
                # 선택된 카테고리의 모든 클러스터 정보 표시
                for idx, (_, cluster_row) in enumerate(filtered_df.iterrows()):
                    cluster_id = cluster_row['cluster_id']
                    cluster_id_str = str(cluster_id)
                    cluster_name = cluster_row.get('cluster_name', f"Cluster_{cluster_id}")
                    topic_category = cluster_row.get('topic_category')
                    # None인 경우 'Unknown'으로 표시하거나 빈 문자열로 처리
                    if pd.isna(topic_category) or topic_category is None:
                        topic_category_display = 'Unknown'
                    else:
                        topic_category_display = topic_category
                    size = cluster_row.get('size', 0)
                    sub_cluster_index = cluster_row.get('sub_cluster_index')
                    
                    # top_keywords는 이미 리스트로 변환되어 있음 (get_clustering_results_from_db에서 처리)
                    top_keywords = cluster_row.get('top_keywords', [])
                    if not isinstance(top_keywords, list):
                        top_keywords = []
                    
                    # post_ids와 representative_post_ids는 이미 리스트로 변환되어 있음
                    post_ids = cluster_row.get('post_ids', [])
                    if not isinstance(post_ids, list):
                        post_ids = []
                    
                    representative_post_ids = cluster_row.get('representative_post_ids', [])
                    if not isinstance(representative_post_ids, list):
                        representative_post_ids = []
                    
                    with st.expander(f"📌 {cluster_name} ({topic_category_display})"):
                        # 기본 정보
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Cluster ID", cluster_id_str)
                        with col2:
                            st.metric("Size", int(size))
                        with col3:
                            st.metric("Sub Cluster Index", sub_cluster_index if pd.notna(sub_cluster_index) else "N/A")
                        with col4:
                            st.metric("Representative", int(cluster_row.get('representative_count', 0)))
                        
                        # DB에서 요약 가져오기 (있으면 표시)
                        summary = cluster_row.get('summary')
                        if pd.notna(summary) and summary:
                            st.markdown("**📝 요약:**")
                            st.info(summary)
                        
                        # GPT로 실시간 요약 생성 (DB 요약이 없거나 추가 요약이 필요한 경우)
                        st.markdown("**📝 요약 (GPT 생성):**")
                        with st.spinner("GPT로 클러스터 요약 생성 중..."):
                            # topic_category가 None인 경우 'Unknown'으로 전달
                            category_for_gpt = topic_category_display if topic_category_display != 'Unknown' else 'Unknown'
                            gpt_summary = generate_cluster_summary(
                                cluster_id_str,
                                top_keywords[:10] if top_keywords else [],  # 상위 10개만
                                int(size),
                                category_for_gpt
                            )
                            if gpt_summary:
                                st.info(gpt_summary)
                            else:
                                st.warning("⚠️ GPT API 호출 실패. OPENAI_API_KEY 환경 변수를 확인하세요.")
                        
                        # Top Keywords
                        if top_keywords:
                            st.markdown("**🔑 주요 키워드:**")
                            keywords_str = ", ".join(top_keywords[:20])  # 상위 20개만 표시
                            st.write(keywords_str)
                            if len(top_keywords) > 20:
                                st.caption(f"총 {len(top_keywords)}개 키워드 중 상위 20개 표시")
                        
                        # Post IDs 통계 (DB에서 조회한 데이터 사용)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Post IDs", len(post_ids))
                        with col2:
                            st.metric("Representative Post IDs", len(representative_post_ids))
                        
                        # 대표 포스트 조회 (DB에서)
                        try:
                            import numpy as np
                            cluster_id_int = int(cluster_id) if not isinstance(cluster_id, (np.integer, np.int64)) else int(cluster_id)
                            representative_posts = get_cluster_representative_posts(cluster_id_int, limit=5)
                            
                            if len(representative_posts) > 0:
                                st.markdown("**📌 대표 포스트:**")
                                for post_idx, (_, post_row) in enumerate(representative_posts.iterrows()):
                                    with st.expander(f"Post {post_idx + 1}: {post_row.get('title', 'N/A')[:50]}..."):
                                        st.write(f"**Title**: {post_row.get('title', 'N/A')}")
                                        st.write(f"**Upvotes**: {post_row.get('upvotes', 0)}")
                                        st.write(f"**Comments**: {post_row.get('num_comments', 0)}")
                                        if post_row.get('permalink'):
                                            st.write(f"**Link**: https://reddit.com{post_row.get('permalink', '')}")
                        except Exception as e:
                            st.debug(f"대표 포스트 조회 오류: {e}")
            else:
                st.info("카테고리 데이터가 없습니다.")
        else:
            # DB와 JSON 모두 실패한 경우
            st.warning("⚠️ 클러스터 데이터를 찾을 수 없습니다.")
            
            # 디버깅 정보 표시
            with st.expander("🔍 디버깅 정보"):
                from db_queries import get_db_connection
                conn = get_db_connection()
                if conn is None:
                    st.error("❌ 데이터베이스 연결 실패")
                    st.info("DATABASE_URL 환경 변수를 확인하세요.")
                else:
                    try:
                        with conn.cursor() as cur:
                            # clusters 테이블 존재 확인
                            cur.execute("""
                                SELECT EXISTS (
                                    SELECT FROM information_schema.tables 
                                    WHERE table_name = 'clusters'
                                )
                            """)
                            table_exists = cur.fetchone()[0]
                            
                            if table_exists:
                                cur.execute("SELECT COUNT(*) FROM clusters WHERE noise_label = FALSE")
                                count = cur.fetchone()[0]
                                st.info(f"✅ clusters 테이블 존재")
                                st.info(f"📊 클러스터 수: {count}")
                                
                                if count == 0:
                                    st.warning("테이블은 존재하지만 데이터가 없습니다.")
                            else:
                                st.error("❌ clusters 테이블이 존재하지 않습니다.")
                    except Exception as db_error:
                        st.error(f"데이터베이스 확인 중 오류: {db_error}")
                    finally:
                        conn.close()
                
    
    except Exception as e:
        st.error(f"클러스터링 결과를 로드하는 중 오류 발생: {e}")
        import traceback
        with st.expander("상세 오류 정보"):
            st.code(traceback.format_exc())
        import traceback
        st.code(traceback.format_exc())

# ============================================================================
# TAB 2: SERP AI Overview
# ============================================================================
with tab2:
    st.header("🔍 SERP AI Overview")
    st.markdown("---")
    
    try:
        serp_df = get_serp_aio()
        
        # 디버깅 정보 표시
        if len(serp_df) == 0:
            st.warning("⚠️ SERP AI Overview 데이터를 조회했지만 결과가 비어있습니다.")
            
            # DB 연결 테스트
            from db_queries import get_db_connection
            conn = get_db_connection()
            if conn is None:
                st.error("❌ 데이터베이스 연결 실패")
                st.info("DATABASE_URL 환경 변수를 확인하세요.")
            else:
                try:
                    with conn.cursor() as cur:
                        # 테이블 존재 확인
                        cur.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'raw_serp_aio'
                            )
                        """)
                        table_exists = cur.fetchone()[0]
                        
                        if table_exists:
                            # 레코드 수 확인
                            cur.execute("SELECT COUNT(*) FROM raw_serp_aio")
                            count = cur.fetchone()[0]
                            st.info(f"✅ 테이블 존재: raw_serp_aio")
                            st.info(f"📊 레코드 수: {count}")
                            
                            if count == 0:
                                st.warning("테이블은 존재하지만 데이터가 없습니다. 데이터 수집 파이프라인을 실행하세요.")
                            else:
                                st.error("데이터는 있지만 쿼리 결과가 비어있습니다. 콘솔 로그를 확인하세요.")
                        else:
                            st.error("❌ raw_serp_aio 테이블이 존재하지 않습니다.")
                            st.info("데이터베이스 마이그레이션을 실행하세요.")
                except Exception as e:
                    st.error(f"데이터베이스 확인 중 오류: {e}")
                finally:
                    conn.close()
        
        if len(serp_df) > 0:
            # 통계 요약 (Error 제외)
            st.subheader("📊 SERP AI Overview 통계")
            
            # Error 제외한 데이터만 사용
            filtered_df = serp_df[serp_df['aio_status'].isin(['AVAILABLE', 'NOT_AVAILABLE'])].copy()
            
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
            
            # 아코디언 형태로 리스트 표시
            st.subheader("📋 SERP 검색 결과")
            st.write(f"**전체 쿼리**: {len(filtered_df)}개")
            
            for idx, row in filtered_df.iterrows():
                # 상태 배지
                if row['aio_status'] == 'AVAILABLE':
                    status_badge = "✅ Available"
                else:
                    status_badge = "❌ Not Available"
                
                # 아코디언 헤더
                expander_title = f"{status_badge} {row['query']}"
                if pd.notna(row.get('snapshot_at')):
                    expander_title += f" ({row['snapshot_at']})"
                
                with st.expander(expander_title):
                    # 입력어 (쿼리)
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**🔍 입력어 (Query)**: `{row['query']}`")
                    with col2:
                        if pd.notna(row.get('snapshot_at')):
                            st.caption(f"📅 {row['snapshot_at']}")
                    
                    # 입력 결과 (AI Overview 텍스트 또는 검색 결과)
                    if row['aio_status'] == 'AVAILABLE' and row.get('aio_text'):
                        st.markdown("**📄 입력 결과 (AI Overview):**")
                        st.info(row['aio_text'])
                    elif row.get('source_table') == 'serp_results':
                        st.markdown("**📄 입력 결과 (검색 결과):**")
                        sources = parse_cited_sources(row.get('cited_sources_json'))
                        if sources:
                            st.info(f"총 {len(sources)}개의 검색 결과가 있습니다.")
                        else:
                            st.info("검색 결과가 없습니다.")
                    else:
                        st.warning(f"입력 결과를 사용할 수 없습니다. (상태: {row['aio_status']})")
                    
                    # 참고 URL (Cited Sources)
                    sources = parse_cited_sources(row.get('cited_sources_json'))
                    if sources:
                        st.markdown("**🔗 참고 URL (Cited Sources):**")
                        
                        # LG 도메인 인용 여부 확인
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
                            # 상위 10개만 표시
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
                    else:
                        st.info("참고 URL 정보가 없습니다.")
            
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
        else:
            st.info("SERP AI Overview 데이터가 없습니다.")
    
    except Exception as e:
        st.error(f"SERP 데이터를 로드하는 중 오류 발생: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.info("데이터베이스 연결을 확인하세요.")

# ============================================================================
# TAB 3: Master Topic
# ============================================================================
with tab3:
    st.header("🎯 Master Topic")
    st.markdown("---")
    
    # Topic Categories
    topic_categories = [
        "SPRING_RECIPES",
        "REFRIGERATOR_ORGANIZATION",
        "VEGETABLE_PREP_HANDLING",
        "SPRING_KITCHEN_STYLING"
    ]
    
    # 저장된 마스터 토픽 결과 파일 경로
    import json
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    master_topics_file = project_root / "data" / "master_topics.json"
    
    # 저장된 결과 로드
    saved_results = {}
    if master_topics_file.exists():
        try:
            with open(master_topics_file, 'r', encoding='utf-8') as f:
                saved_results = json.load(f)
        except Exception as e:
            st.error(f"❌ 저장된 결과 파일을 읽는 중 오류 발생: {e}")
            saved_results = {}
    else:
        st.error("❌ 저장된 마스터 토픽 결과 파일을 찾을 수 없습니다.")
        st.info(f"파일 경로: {master_topics_file}")
        st.info("콘솔에서 `python3 generate_master_topics_console.py`를 실행하여 결과를 생성하세요.")
        st.stop()
    
    # 저장된 결과 표시
    if saved_results:
        for idx, topic_category in enumerate(topic_categories):
            if topic_category in saved_results:
                st.markdown("---")
                st.subheader(f"## {topic_category}")
                st.markdown(saved_results[topic_category])
            else:
                st.markdown("---")
                st.subheader(f"## {topic_category}")
                st.warning(f"⚠️ {topic_category}에 대한 저장된 결과가 없습니다.")
        
        # 전체 결과 다운로드 버튼
        st.markdown("---")
        full_result_text = "\n\n\n".join([
            f"==============================\n## {cat}\n==============================\n{result}"
            for cat, result in saved_results.items()
        ])
        full_result_text += "\n\n======================================================================\n=== GPT 마스터 토픽 생성 완료 ===\n======================================================================"
        
        st.download_button(
            "📥 전체 결과 다운로드 (텍스트)",
            full_result_text,
            "master_topics_all_categories.txt",
            "text/plain",
            key="download_all_results"
        )
    else:
        st.warning("⚠️ 표시할 마스터 토픽 결과가 없습니다.")
        st.info("콘솔에서 `python3 generate_master_topics_console.py`를 실행하여 결과를 생성하세요.")

# ============================================================================
# Footer
# ============================================================================
st.markdown("---")
st.markdown("**Note**: This dashboard is read-only. Data collection and analysis are performed separately via the pipeline.")
