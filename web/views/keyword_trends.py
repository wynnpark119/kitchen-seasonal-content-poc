"""
키워드 트렌드 모니터링 뷰

2025년 키워드별 검색량 및 Reddit 게시물 수 추이를 시각화
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from common.file_loader import load_json
from web.components import render_insight_card


def load_trends_data() -> Optional[Dict]:
    """키워드 트렌드 JSON 데이터 로드"""
    data = load_json("trends_2025.json", required=False)
    
    if data is None:
        st.warning("⚠️ 키워드 트렌드 데이터 파일을 찾을 수 없습니다.")
        st.info("💡 `data/trends_2025.json` 파일이 존재하는지 확인하세요.")
    
    return data


def calculate_kpi_stats(data: Dict) -> Dict[str, Dict]:
    """KPI 통계 계산"""
    keywords = data.get("keywords", [])
    months = data.get("months", [])
    
    stats = {}
    
    for keyword in keywords:
        search_indices = []
        reddit_posts = []
        search_peaks = []
        reddit_peaks = []
        
        for month_data in months:
            series = month_data.get("series", {}).get(keyword, {})
            search_idx = series.get("search_index", 0)
            reddit_count = series.get("reddit_posts", 0)
            
            search_indices.append(search_idx)
            reddit_posts.append(reddit_count)
            
            # 피크 월 찾기 (간단히 최대값)
            if search_idx == max([m["series"].get(keyword, {}).get("search_index", 0) for m in months]):
                search_peaks.append(month_data["month"])
            if reddit_count == max([m["series"].get(keyword, {}).get("reddit_posts", 0) for m in months]):
                reddit_peaks.append(month_data["month"])
        
        avg_search_index = sum(search_indices) / len(search_indices) if search_indices else 0
        total_reddit_posts = sum(reddit_posts)
        
        stats[keyword] = {
            "avg_search_index": round(avg_search_index, 1),
            "total_reddit_posts": total_reddit_posts,
            "peak_search_month": search_peaks[0] if search_peaks else None,
            "peak_reddit_month": reddit_peaks[0] if reddit_peaks else None,
        }
    
    return stats


def create_trend_chart(data: Dict) -> go.Figure:
    """키워드 트렌드 차트 생성"""
    keywords = data.get("keywords", [])
    months = data.get("months", [])
    
    # 서브플롯 생성 (secondary y-axis 사용)
    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        vertical_spacing=0.1
    )
    
    # 각 키워드별로 데이터 준비
    for keyword in keywords:
        months_list = []
        search_indices = []
        reddit_posts = []
        reasons = []  # 변곡점 reason 저장
        
        for month_data in months:
            month = month_data["month"]
            series = month_data.get("series", {}).get(keyword, {})
            search_idx = series.get("search_index", 0)
            reddit_count = series.get("reddit_posts", 0)
            
            months_list.append(month)
            search_indices.append(search_idx)
            reddit_posts.append(reddit_count)
            
            # 해당 월의 turning_points에서 이 키워드의 reason 찾기
            turning_points = month_data.get("turning_points", [])
            reason = ""
            for tp in turning_points:
                if tp.get("keyword") == keyword:
                    reason = tp.get("reason", "")
                    break
            reasons.append(reason)
        
        # Search Index 라인 차트 (왼쪽 Y축)
        # customdata: [reddit_posts, reason] 형태로 저장
        customdata_search = []
        for reddit, reason in zip(reddit_posts, reasons):
            customdata_search.append([reddit, reason if reason else ""])
        
        fig.add_trace(
            go.Scatter(
                x=months_list,
                y=search_indices,
                name=f"{keyword} - Search Index",
                mode="lines+markers",
                line=dict(width=2),
                marker=dict(size=6),
                customdata=customdata_search,
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Month: %{x}<br>"
                    "Search Index: %{y}<br>"
                    "Reddit Posts: %{customdata[0]}<br>"
                    "%{customdata[1]}<extra></extra>"
                ),
            ),
            secondary_y=False,
        )
        
        # Reddit Posts 점선 라인 차트 (오른쪽 Y축)
        # customdata: [search_index, reason] 형태로 저장
        customdata_reddit = []
        for search_idx, reason in zip(search_indices, reasons):
            customdata_reddit.append([search_idx, reason if reason else ""])
        
        fig.add_trace(
            go.Scatter(
                x=months_list,
                y=reddit_posts,
                name=f"{keyword} - Reddit Posts",
                mode="lines+markers",
                line=dict(width=2, dash="dash"),
                marker=dict(size=6),
                customdata=customdata_reddit,
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Month: %{x}<br>"
                    "Reddit Posts: %{y}<br>"
                    "Search Index: %{customdata[0]}<br>"
                    "%{customdata[1]}<extra></extra>"
                ),
            ),
            secondary_y=True,
        )
    
    # 레이아웃 설정
    fig.update_layout(
        title="",
        height=500,
        hovermode="x unified",
        template="plotly_dark",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=30, b=50),
    )
    
    # Y축 레이블 설정
    fig.update_xaxes(title_text="Month", tickangle=-45)
    fig.update_yaxes(title_text="Search Index (0-100)", secondary_y=False)
    fig.update_yaxes(title_text="Reddit Posts (count)", secondary_y=True)
    
    return fig


def render_keyword_trends():
    """키워드 트렌드 모니터링 페이지 렌더링"""
    
    # 데이터 로드
    data = load_trends_data()
    if data is None:
        return
    
    # KPI 통계 계산
    stats = calculate_kpi_stats(data)
    
    # KPI 카드 표시 (다른 페이지 스타일 참조)
    recipe_stats = stats.get("recipe", {})
    microwave_stats = stats.get("microwave recipe", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_insight_card(
            title="recipe - 평균 검색 지수",
            value=f"{recipe_stats.get('avg_search_index', 0)}",
            description="",
            color="#2196F3"
        )
    
    with col2:
        render_insight_card(
            title="recipe - 총 Reddit 게시물",
            value=f"{recipe_stats.get('total_reddit_posts', 0):,}개",
            description="",
            color="#4CAF50"
        )
    
    with col3:
        render_insight_card(
            title="microwave recipe - 평균 검색 지수",
            value=f"{microwave_stats.get('avg_search_index', 0)}",
            description="",
            color="#FF9800"
        )
    
    with col4:
        render_insight_card(
            title="microwave recipe - 총 Reddit 게시물",
            value=f"{microwave_stats.get('total_reddit_posts', 0):,}개",
            description="",
            color="#9E9E9E"
        )
    
    # 차트 표시
    st.markdown("---")
    fig = create_trend_chart(data)
    st.plotly_chart(fig, use_container_width=True)
    
    # 변곡점 안내
    st.caption("💡 변곡점(변화 이유가 있는 월)에 마우스를 올리면 상세 이유가 표시됩니다.")
