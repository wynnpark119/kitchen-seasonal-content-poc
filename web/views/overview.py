"""
Overview 페이지 뷰

Dashboard Home 구조로 데이터 현황만 요약 표시
- 해석·인사이트 없이 데이터 결과만 표시
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import json

from web.components import render_insight_card
from web.db_queries import (
    get_db_connection,
    get_serp_aio,
    parse_cited_sources,
    get_master_topics,
    get_clustering_results_from_db
)
from services.serp_service import get_serp_service

# 프로젝트 루트 경로
project_root = Path(__file__).parent.parent.parent
data_dir = project_root / "data"


def get_keyword_stats() -> Dict[str, any]:
    """Google 검색 결과 현황 데이터 조회"""
    json_path = data_dir / "keyword_msv_table.json"
    
    if not json_path.exists():
        return {
            "total_keywords": 0,
            "aio_trigger_count": 0,
            "top_keywords": []
        }
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get('items', [])
        if not items:
            return {
                "total_keywords": 0,
                "aio_trigger_count": 0,
                "top_keywords": []
            }
        
        df = pd.DataFrame(items)
        total_keywords = len(df)
        
        # AIO 트리거 키워드 수
        aio_count = df['aio'].sum() if 'aio' in df.columns else 0
        
        # 상위 키워드 Top 3
        top_keywords = []
        if 'msv_google_worldwide' in df.columns:
            top_msv = df.nlargest(3, 'msv_google_worldwide')
            top_keywords = top_msv['keyword'].head(3).tolist()
        
        return {
            "total_keywords": total_keywords,
            "aio_trigger_count": aio_count,
            "top_keywords": top_keywords
        }
    except Exception as e:
        print(f"Error loading keyword stats: {e}")
        return {
            "total_keywords": 0,
            "aio_trigger_count": 0,
            "top_keywords": []
        }


def get_reddit_category_stats() -> Dict[str, Dict[str, int]]:
    """Reddit 게시물 수집 현황: 카테고리별 총 게시물 수와 태그 분류"""
    # JSON 파일에서 태그 정보 가져오기 (reddit_collection_posts.py와 동일한 방식)
    json_path = data_dir / "reddit_posts_data.json"
    
    category_stats = {}
    
    # 기본값 설정
    for category in ['SPRING_RECIPES', 'SPRING_KITCHEN_STYLING', 'REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING']:
        category_stats[category] = {
            "total": 0,
            "seasonal": 0,
            "evergreen": 0,
            "other": 0
        }
    
    if not json_path.exists():
        # JSON 파일이 없으면 DB에서 카테고리별 게시물 수만 가져오기
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            c.topic_category,
                            SUM(c.size) as total_posts
                        FROM clusters c
                        WHERE c.noise_label = FALSE
                        AND c.topic_category IN ('SPRING_RECIPES', 'SPRING_KITCHEN_STYLING', 
                                                 'REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING')
                        GROUP BY c.topic_category
                    """)
                    
                    for row in cur.fetchall():
                        category = row[0]
                        total_posts = row[1] or 0
                        if category in category_stats:
                            category_stats[category]["total"] = total_posts
            except Exception as e:
                print(f"Error getting Reddit category stats from DB: {e}")
            finally:
                conn.close()
        
        return category_stats
    
    try:
        # JSON 파일에서 태그 정보 가져오기
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 데이터 정규화 (reddit_collection_posts.py의 normalize_json_data와 동일)
        normalized = {}
        
        if isinstance(data, dict) and "topic_category" in data:
            category = data["topic_category"]
            posts = data.get("posts", [])
            normalized[category] = posts
        elif isinstance(data, dict) and "data" in data:
            for item in data["data"]:
                if isinstance(item, dict) and "topic_category" in item:
                    category = item["topic_category"]
                    posts = item.get("posts", [])
                    if category not in normalized:
                        normalized[category] = []
                    normalized[category].extend(posts)
        elif isinstance(data, dict) and "categories" in data:
            for category, category_data in data["categories"].items():
                if isinstance(category_data, dict) and "posts" in category_data:
                    normalized[category] = category_data["posts"]
                elif isinstance(category_data, list):
                    normalized[category] = category_data
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "topic_category" in item:
                    category = item["topic_category"]
                    posts = item.get("posts", [])
                    if category not in normalized:
                        normalized[category] = []
                    normalized[category].extend(posts)
        
        # 태그 정규화 및 통계 계산
        for category in ['SPRING_RECIPES', 'SPRING_KITCHEN_STYLING', 'REFRIGERATOR_ORGANIZATION', 'VEGETABLE_PREP_HANDLING']:
            posts = normalized.get(category, [])
            total_posts = len(posts)
            
            seasonal_count = 0
            evergreen_count = 0
            other_count = 0
            
            for post in posts:
                # 태그 정규화 (reddit_collection_posts.py의 normalize_json_data와 동일한 방식)
                if "tag" in post and "tags" not in post:
                    tags = [post["tag"]] if isinstance(post["tag"], str) else post["tag"]
                elif "tags" in post:
                    tags = post["tags"]
                    if isinstance(tags, str):
                        tags = [tags]
                else:
                    tags = ["other"]  # 태그가 없으면 other로 설정
                
                # 태그가 리스트가 아니면 리스트로 변환
                if not isinstance(tags, list):
                    tags = ["other"]
                
                # 태그별 카운트 (모든 태그 카운트)
                for tag in tags:
                    tag_lower = tag.lower() if isinstance(tag, str) else str(tag).lower()
                    if tag_lower == "seasonal":
                        seasonal_count += 1
                    elif tag_lower == "evergreen":
                        evergreen_count += 1
                    else:
                        other_count += 1
            
            category_stats[category] = {
                "total": total_posts,
                "seasonal": seasonal_count,
                "evergreen": evergreen_count,
                "other": other_count
            }
        
        return category_stats
    except Exception as e:
        print(f"Error getting Reddit category stats from JSON: {e}")
        return category_stats


def get_ai_overview_stats() -> Dict[str, Dict[str, any]]:
    """AI 오버뷰 분석: 소스 타입별 개수와 비율"""
    try:
        serp_service = get_serp_service()
        serp_df = serp_service.get_all_serp_data()
        
        if serp_df is None or len(serp_df) == 0:
            return {
                "lg_owned": {"count": 0, "ratio": 0.0},
                "competitor": {"count": 0, "ratio": 0.0},
                "earned_media": {"count": 0, "ratio": 0.0},
                "other": {"count": 0, "ratio": 0.0}
            }
        
        filtered_df = serp_df[serp_df['aio_status'].isin(['AVAILABLE', 'NOT_AVAILABLE'])].copy()
        
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
        
        return {
            "lg_owned": {
                "count": total_lg_owned,
                "ratio": (total_lg_owned / total_sources * 100) if total_sources > 0 else 0.0
            },
            "competitor": {
                "count": total_competitor,
                "ratio": (total_competitor / total_sources * 100) if total_sources > 0 else 0.0
            },
            "earned_media": {
                "count": total_earned_media,
                "ratio": (total_earned_media / total_sources * 100) if total_sources > 0 else 0.0
            },
            "other": {
                "count": total_other,
                "ratio": (total_other / total_sources * 100) if total_sources > 0 else 0.0
            }
        }
    except Exception as e:
        print(f"Error getting AI overview stats: {e}")
        return {
            "lg_owned": {"count": 0, "ratio": 0.0},
            "competitor": {"count": 0, "ratio": 0.0},
            "earned_media": {"count": 0, "ratio": 0.0},
            "other": {"count": 0, "ratio": 0.0}
        }


def get_reddit_analysis_summary() -> Dict[str, any]:
    """Reddit 토픽 분석 요약: 클러스터링 결과 개수, 클러스터링 결과 일부"""
    try:
        # 클러스터링 결과 개수
        clusters_df = get_clustering_results_from_db()
        cluster_count = len(clusters_df) if clusters_df is not None else 0
        
        # 클러스터링 결과 일부 제목 리스트 (2~3개) - 클러스터에서 가져오기
        cluster_titles = []
        if clusters_df is not None and len(clusters_df) > 0:
            # 클러스터 제목 또는 대표 키워드 가져오기
            for idx, row in clusters_df.head(3).iterrows():
                # cluster_title, topic_title, 또는 대표 키워드 사용
                title = row.get('cluster_title') or row.get('topic_title') or row.get('representative_keyword', '')
                if title:
                    cluster_titles.append(str(title))
        
        return {
            "cluster_count": cluster_count,
            "cluster_titles": cluster_titles
        }
    except Exception as e:
        print(f"Error getting Reddit analysis summary: {e}")
        import traceback
        traceback.print_exc()
        return {
            "cluster_count": 0,
            "cluster_titles": []
        }


def get_master_topics_summary() -> Dict[str, any]:
    """Master Topic 제안 요약: 생성된 마스터 토픽 개수, 토픽 제목 리스트 일부"""
    # JSON 파일에서 읽기 (DB 사용 안 함)
    json_path = data_dir / "master_topics_final_kr_en_RICH_WHY.json"
    
    if not json_path.exists():
        return {
            "total_count": 0,
            "topic_titles": []
        }
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            topics_data = json.load(f)
        
        # 카테고리별로 그룹화된 데이터에서 모든 토픽 수집
        all_topics = []
        if isinstance(topics_data, dict):
            for category, topics_list in topics_data.items():
                if isinstance(topics_list, list):
                    for topic in topics_list:
                        if isinstance(topic, dict):
                            # master_topic_kr 또는 topic_title 필드 확인
                            title = topic.get('master_topic_kr') or topic.get('topic_title') or topic.get('title', '')
                            if title:
                                all_topics.append(title)
        
        total_count = len(all_topics)
        # 상위 5개만 가져오기
        topic_titles = all_topics[:5]
        
        return {
            "total_count": total_count,
            "topic_titles": topic_titles
        }
    except Exception as e:
        print(f"Error getting master topics summary from JSON: {e}")
        import traceback
        traceback.print_exc()
        return {
            "total_count": 0,
            "topic_titles": []
        }


def render_overview():
    """Overview 페이지 렌더링"""
    
    # 1. Master Topic Overview (미리보기) - 최상단 배치
    col_title1, col_icon1 = st.columns([20, 1])
    with col_title1:
        st.markdown("### Master Topic Overview")
    with col_icon1:
        if st.button("🔗", key="icon_master_topics", help="상세 페이지로 이동", use_container_width=False):
            st.session_state.selected_page = "master_topics"
            st.rerun()
    
    master_topics_summary = get_master_topics_summary()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(
            f"""
            <div style="
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                background-color: #262730;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                min-height: 180px;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            ">
                <div style="color: #888888; font-size: 0.85rem; margin-bottom: 6px; line-height: 1.4;">
                    생성된 마스터 토픽 개수
                </div>
                <div style="color: #2196F3; font-size: 1.75rem; font-weight: bold; margin-bottom: 6px; line-height: 1.2; flex-grow: 1; display: flex; align-items: center;">
                    {master_topics_summary['total_count']:,}개
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        topic_titles = master_topics_summary.get("topic_titles", [])
        if topic_titles:
            # 각 토픽을 줄바꿈으로 구분하여 HTML로 표시
            titles_html = "<br>".join([f"• {title}" for title in topic_titles])
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    background-color: #262730;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    min-height: 180px;
                    display: flex;
                    flex-direction: column;
                    justify-content: flex-start;
                ">
                    <div style="color: #888888; font-size: 0.85rem; margin-bottom: 6px; line-height: 1.4;">
                        토픽 제목 리스트 일부
                    </div>
                    <div style="color: #4CAF50; font-size: 0.75rem; line-height: 1.8; flex-grow: 1; overflow-wrap: break-word; word-wrap: break-word;">
                        {titles_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            render_insight_card(
                title="토픽 제목 리스트 일부",
                value="없음",
                description="",
                color="#9E9E9E"
            )
    
    st.markdown("---")
    
    # 2. Google 검색 결과 현황 (Summary Cards)
    col_title2, col_icon2 = st.columns([20, 1])
    with col_title2:
        st.markdown("### Google 검색 결과 현황")
    with col_icon2:
        if st.button("🔗", key="icon_exploration_status", help="상세 페이지로 이동", use_container_width=False):
            st.session_state.selected_page = "exploration_status"
            st.rerun()
    
    keyword_stats = get_keyword_stats()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_insight_card(
            title="전체 키워드 수",
            value=f"{keyword_stats['total_keywords']:,}개",
            description="",
            color="#2196F3"
        )
    
    with col2:
        render_insight_card(
            title="AIO 트리거 키워드 수",
            value=f"{keyword_stats['aio_trigger_count']:,}개",
            description="",
            color="#FF9800"
        )
    
    with col3:
        top_keywords = keyword_stats['top_keywords']
        if top_keywords and len(top_keywords) > 0:
            # 키워드를 세로로 나열하여 표시 (폰트 크기 조정, 높이 맞춤)
            keywords_html = "<br>".join([f"• {kw}" for kw in top_keywords[:3]])
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
                        상위 키워드 Top 3
                    </div>
                    <div style="color: #4CAF50; font-size: 1rem; font-weight: 500; line-height: 1.6; flex-grow: 1; display: flex; align-items: flex-start;">
                        {keywords_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            render_insight_card(
                title="상위 키워드 Top 3",
                value="N/A",
                description="",
                color="#9E9E9E"
            )
    
    st.markdown("---")
    
    # 3. Reddit 게시물 수집 현황 (Topic Category Cards)
    col_title3, col_icon3 = st.columns([20, 1])
    with col_title3:
        st.markdown("### Reddit 게시물 수집 현황")
    with col_icon3:
        if st.button("🔗", key="icon_reddit_collection_posts", help="상세 페이지로 이동", use_container_width=False):
            st.session_state.selected_page = "reddit_collection_posts"
            st.rerun()
    
    category_stats = get_reddit_category_stats()
    
    category_labels = {
        "SPRING_RECIPES": "Spring Recipes",
        "SPRING_KITCHEN_STYLING": "Spring Kitchen Styling",
        "REFRIGERATOR_ORGANIZATION": "Refrigerator Organization",
        "VEGETABLE_PREP_HANDLING": "Vegetable Prep Handling"
    }
    
    category_order = [
        "SPRING_RECIPES",
        "SPRING_KITCHEN_STYLING",
        "REFRIGERATOR_ORGANIZATION",
        "VEGETABLE_PREP_HANDLING"
    ]
    
    cols = st.columns(4)
    
    for idx, category in enumerate(category_order):
        stats = category_stats.get(category, {
            "total": 0,
            "seasonal": 0,
            "evergreen": 0,
            "other": 0
        })
        
        # 태그별 색상 정의
        tag_colors = {
            "seasonal": "#4CAF50",  # 녹색
            "evergreen": "#2196F3",  # 파란색
            "other": "#9E9E9E"  # 회색
        }
        
        # 태그 분류 텍스트 생성 (0개인 항목은 제외, 색상 적용)
        tag_parts = []
        if stats['seasonal'] > 0:
            tag_parts.append(f'<span style="color: {tag_colors["seasonal"]}; font-weight: 600;">seasonal {stats["seasonal"]}개</span>')
        if stats['evergreen'] > 0:
            tag_parts.append(f'<span style="color: {tag_colors["evergreen"]}; font-weight: 600;">evergreen {stats["evergreen"]}개</span>')
        if stats['other'] > 0:
            tag_parts.append(f'<span style="color: {tag_colors["other"]}; font-weight: 600;">other {stats["other"]}개</span>')
        
        tag_text = "<br>".join(tag_parts) if tag_parts else "데이터 없음"
        
        with cols[idx]:
            # 커스텀 카드 렌더링 (HTML 태그가 제대로 렌더링되도록)
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
                        {category_labels[category]}
                    </div>
                    <div style="font-size: 0.75rem; line-height: 1.8; flex-grow: 1;">
                        {tag_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    st.markdown("---")
    
    # 4. AI 오버뷰 분석 (Source Type Cards)
    col_title4, col_icon4 = st.columns([20, 1])
    with col_title4:
        st.markdown("### AI 오버뷰 분석")
    with col_icon4:
        if st.button("🔗", key="icon_ai_overview", help="상세 페이지로 이동", use_container_width=False):
            st.session_state.selected_page = "ai_overview"
            st.rerun()
    
    ai_overview_stats = get_ai_overview_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        lg_stats = ai_overview_stats.get("lg_owned", {"count": 0, "ratio": 0.0})
        render_insight_card(
            title="LG Owned",
            value=f"{lg_stats['count']:,}개",
            description=f"전체의 {lg_stats['ratio']:.1f}%",
            color="#2196F3"
        )
    
    with col2:
        competitor_stats = ai_overview_stats.get("competitor", {"count": 0, "ratio": 0.0})
        render_insight_card(
            title="Competitor",
            value=f"{competitor_stats['count']:,}개",
            description=f"전체의 {competitor_stats['ratio']:.1f}%",
            color="#FF9800"
        )
    
    with col3:
        earned_stats = ai_overview_stats.get("earned_media", {"count": 0, "ratio": 0.0})
        render_insight_card(
            title="Earned Media",
            value=f"{earned_stats['count']:,}개",
            description=f"전체의 {earned_stats['ratio']:.1f}%",
            color="#4CAF50"
        )
    
    with col4:
        other_stats = ai_overview_stats.get("other", {"count": 0, "ratio": 0.0})
        render_insight_card(
            title="Other",
            value=f"{other_stats['count']:,}개",
            description=f"전체의 {other_stats['ratio']:.1f}%",
            color="#9E9E9E"
        )
    
