"""
레딧 게시물 수집 현황 뷰

각 카테고리별 게시물을 탭으로 분리하여 표시
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from web.components import render_insight_card


def normalize_json_data(data: Any) -> Dict[str, List[Dict]]:
    """
    다양한 형태의 JSON 데이터를 정규화된 형태로 변환
    
    정규화된 형태:
    {
        "SPRING_RECIPES": [ {title, reply, tag/tags}, ... ],
        "SPRING_KITCHEN_STYLING": [...],
        "REFRIGERATOR_ORGANIZATION": [...],
        "VEGETABLE_PREP_HANDLING": [...]
    }
    """
    normalized = {}
    
    # 형태 A: {"topic_category": "...", "posts": [...]}
    if isinstance(data, dict) and "topic_category" in data:
        category = data["topic_category"]
        posts = data.get("posts", [])
        normalized[category] = posts
    
    # 형태 B: {"data": [{"topic_category": "...", "posts": [...]}, ...]}
    elif isinstance(data, dict) and "data" in data:
        for item in data["data"]:
            if isinstance(item, dict) and "topic_category" in item:
                category = item["topic_category"]
                posts = item.get("posts", [])
                if category not in normalized:
                    normalized[category] = []
                normalized[category].extend(posts)
    
    # 형태 C: {"categories": {"SPRING_RECIPES": {...}, ...}}
    elif isinstance(data, dict) and "categories" in data:
        for category, category_data in data["categories"].items():
            if isinstance(category_data, dict) and "posts" in category_data:
                normalized[category] = category_data["posts"]
            elif isinstance(category_data, list):
                normalized[category] = category_data
    
    # 형태 D: 배열 형태 [{"topic_category": "...", "posts": [...]}, ...]
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "topic_category" in item:
                category = item["topic_category"]
                posts = item.get("posts", [])
                if category not in normalized:
                    normalized[category] = []
                normalized[category].extend(posts)
    
    # 태그 정규화 (tag/tags 통일)
    for category in normalized:
        for post in normalized[category]:
            if "tag" in post and "tags" not in post:
                post["tags"] = [post["tag"]] if isinstance(post["tag"], str) else post["tag"]
            elif "tags" in post and isinstance(post["tags"], str):
                post["tags"] = [post["tags"]]
            elif "tags" not in post:
                post["tags"] = ["other"]
    
    return normalized






def load_reddit_posts_data(file_path: Path = None) -> Dict[str, List[Dict]]:
    """
    레딧 게시물 데이터 로드
    """
    if file_path is None:
        file_path = project_root / "data" / "reddit_posts_data.json"
    
    if not file_path.exists():
        st.warning(f"⚠️ JSON 파일을 찾을 수 없습니다: {file_path}")
        st.info(f"💡 파일 경로를 확인해주세요: `{file_path}`")
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        normalized = normalize_json_data(data)
        return normalized
    
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON 파싱 오류: {e}")
        return {}
    except Exception as e:
        st.error(f"❌ 파일 로드 오류: {e}")
        return {}


def render_category_tab(category: str, posts: List[Dict]):
    """카테고리별 탭 렌더링 - DataFrame 테이블 형태 (최대 50개)"""
    if not posts:
        st.info("게시물이 없습니다.")
        return
    
    # 최대 50개만 표시
    display_posts = posts[:50]
    
    # DataFrame 생성
    rows = []
    for post in display_posts:
        title = post.get("title", "")
        reply = post.get("reply", "")
        tags = post.get("tags", [])
        
        # 태그 정규화
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = ["other"]
        
        # 태그를 문자열로 변환
        tags_str = ", ".join(tags) if tags else "other"
        
        rows.append({
            "제목": title,
            "대표 답변": reply,
            "태그": tags_str
        })
    
    df = pd.DataFrame(rows)
    
    # 테이블 표시 (구글 검색 현황과 동일한 스타일)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
    
    # 전체 게시물 수와 표시된 게시물 수 안내
    if len(posts) > 50:
        st.caption(f"전체 {len(posts)}개 중 상위 50개 게시물만 표시됩니다.")


def calculate_tag_stats(posts: List[Dict]) -> Dict[str, int]:
    """카테고리별 태그 통계 계산"""
    tag_counter = Counter()
    
    for post in posts:
        tags = post.get("tags", [])
        
        # 태그 정규화
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = ["other"]
        
        for tag in tags:
            tag_counter[tag.lower()] += 1
    
    return dict(tag_counter)


def render_reddit_collection_posts():
    """레딧 게시물 수집 현황 페이지 렌더링"""
    
    # 데이터 로드
    data = load_reddit_posts_data()
    
    if not data:
        st.warning("⚠️ 레딧 게시물 데이터가 없습니다.")
        return
    
    # 카테고리 순서 정의
    category_order = [
        "SPRING_RECIPES",
        "SPRING_KITCHEN_STYLING",
        "REFRIGERATOR_ORGANIZATION",
        "VEGETABLE_PREP_HANDLING"
    ]
    
    # 존재하는 카테고리만 필터링
    available_categories = [cat for cat in category_order if cat in data]
    
    if not available_categories:
        st.warning("⚠️ 표시할 카테고리가 없습니다.")
        return
    
    # 각 카테고리별 태그 통계 계산 및 카드 표시
    cols = st.columns(len(available_categories))
    
    # 태그별 색상 정의
    tag_colors = {
        "seasonal": "#4CAF50",  # 녹색
        "evergreen": "#2196F3",  # 파란색
        "other": "#9E9E9E"  # 회색
    }
    
    for idx, category in enumerate(available_categories):
        posts = data[category]
        tag_stats = calculate_tag_stats(posts)
        
        # 태그별 개수 추출
        seasonal_count = tag_stats.get("seasonal", 0)
        evergreen_count = tag_stats.get("evergreen", 0)
        other_count = tag_stats.get("other", 0)
        total_tags = seasonal_count + evergreen_count + other_count
        
        # 태그 통계 HTML 생성 (색상 적용)
        tag_summary_parts = []
        if seasonal_count > 0:
            tag_summary_parts.append(
                f'<span style="color: {tag_colors["seasonal"]}; font-weight: 600;">seasonal {seasonal_count}개</span>'
            )
        if evergreen_count > 0:
            tag_summary_parts.append(
                f'<span style="color: {tag_colors["evergreen"]}; font-weight: 600;">evergreen {evergreen_count}개</span>'
            )
        if other_count > 0:
            tag_summary_parts.append(
                f'<span style="color: {tag_colors["other"]}; font-weight: 600;">other {other_count}개</span>'
            )
        
        tag_summary_html = ", ".join(tag_summary_parts) if tag_summary_parts else "태그 없음"
        
        with cols[idx]:
            display_name = category.replace("_", " ").title()
            render_insight_card(
                title=display_name,
                value=f"{total_tags}개",
                description=tag_summary_html,
                color="#2196F3"
            )
    
    st.markdown("---")
    
    # 탭으로 게시물 표시
    tab_labels = [cat.replace("_", " ").title() for cat in available_categories]
    tabs = st.tabs(tab_labels)
    
    for tab, category in zip(tabs, available_categories):
        with tab:
            posts = data[category]
            render_category_tab(category, posts)
