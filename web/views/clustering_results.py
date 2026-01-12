"""
Clustering Results 뷰

클러스터링 결과 표시
"""
import streamlit as st
import pandas as pd
from typing import Optional
import importlib
import sys
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 모듈 재로드를 위해 import
from services import clustering_service
from services.gpt_service import get_gpt_service
from common.openai_client import is_openai_available
from web.db_queries import get_category_cluster_distribution

# Streamlit 모듈 캐싱 문제 해결: 모듈 재로드
if 'services.clustering_service' in sys.modules:
    importlib.reload(clustering_service)


def render_clustering_results():
    """Reddit 토픽 분석 탭 렌더링"""
    # 재로드된 모듈에서 함수 가져오기
    clustering_service_instance = clustering_service.get_clustering_service()
    gpt_service = get_gpt_service()
    
    try:
        clusters_df = clustering_service_instance.get_all_clusters()
        
        if len(clusters_df) == 0:
            st.warning("⚠️ Reddit 토픽 분석 데이터가 없습니다.")
            st.info("클러스터링이 완료되면 결과가 표시됩니다.")
            return
        
        # ========================================================================
        # 📌 카테고리별 포스트 분포 & 클러스터 주제 시각화 섹션
        # ========================================================================
        st.markdown("### 📌 카테고리별 포스트 분포 & 클러스터 주제")
        
        try:
            # clusters_df를 직접 사용하여 Treemap 데이터 생성 (아래 클러스터링 결과와 동일한 데이터 소스)
            if len(clusters_df) > 0 and 'topic_category' in clusters_df.columns:
                # clusters_df에서 필요한 데이터 생성
                dist_data = []
                for _, row in clusters_df.iterrows():
                    if pd.notna(row.get('topic_category')) and row.get('size', 0) > 0:
                        cluster_name = row.get('cluster_name')
                        if not cluster_name:
                            # cluster_name이 없으면 생성
                            topic_category = row.get('topic_category')
                            sub_cluster_index = row.get('sub_cluster_index')
                            if pd.notna(sub_cluster_index):
                                cluster_name = f"{topic_category}_{int(sub_cluster_index) + 1}"
                            else:
                                cluster_name = f"Cluster_{row.get('cluster_id', '')}"
                        
                        dist_data.append({
                            'topic_category': row.get('topic_category'),
                            'cluster_name': cluster_name,
                            'post_count': int(row.get('size', 0)),
                            'top_keywords': row.get('top_keywords', []),
                            'summary': row.get('summary', ''),
                            'cluster_id': row.get('cluster_id')
                        })
                dist_df = pd.DataFrame(dist_data)
            else:
                dist_df = pd.DataFrame()
            
            if len(dist_df) == 0:
                st.warning("⚠️ 카테고리별 클러스터 분포 데이터가 없습니다.")
            else:
                # Treemap 데이터 준비
                st.markdown("#### 카테고리별 클러스터 비중 Treemap")
                
                # Treemap용 계층 구조 데이터 생성
                treemap_data = []
                keywords_map = {}  # 클러스터명 -> 전체 키워드 매핑 (hover용)
                summary_map = {}  # 클러스터명 -> 요약 매핑 (hover용)
                
                # 먼저 클러스터 레벨 추가
                for _, row in dist_df.iterrows():
                    cluster_name = row['cluster_name']
                    top_keywords = row.get('top_keywords', [])
                    summary = row.get('summary', '')
                    
                    # 차트에 표시할 키워드 (상위 5개만)
                    keywords_list_display = []
                    # hover용 전체 키워드 (최대 20개)
                    keywords_list_full = []
                    
                    if top_keywords:
                        if isinstance(top_keywords, list):
                            keywords_list_display = top_keywords[:5]
                            keywords_list_full = top_keywords[:20]  # hover용 전체 키워드
                        elif isinstance(top_keywords, str):
                            # JSON 문자열인 경우 파싱 시도
                            try:
                                import json
                                parsed = json.loads(top_keywords)
                                if isinstance(parsed, list):
                                    keywords_list_display = parsed[:5]
                                    keywords_list_full = parsed[:20]
                            except:
                                pass
                    
                    # 차트에 표시할 키워드 (상위 5개)
                    keywords_str_display = ', '.join(keywords_list_display) if keywords_list_display else ""
                    # hover용 전체 키워드
                    keywords_str_full = ', '.join(keywords_list_full) if keywords_list_full else ""
                    
                    # 키워드 매핑 저장 (hover용 - 전체 키워드)
                    keywords_map[cluster_name] = keywords_str_full
                    
                    # 요약 매핑 저장 (hover용 - 전체 요약)
                    if summary and pd.notna(summary) and str(summary).strip():
                        summary_str = str(summary).strip()
                        # hover에는 전체 요약 표시
                        summary_map[cluster_name] = summary_str
                    else:
                        summary_map[cluster_name] = ""
                    
                    # 차트에 표시할 텍스트: 클러스터명 + 키워드 (상위 5개)
                    if keywords_str_display:
                        display_text = f"{cluster_name}<br><span style='font-size:0.85em;'>{keywords_str_display}</span>"
                    else:
                        display_text = cluster_name
                    
                    treemap_data.append({
                        'labels': cluster_name,  # 기본 레이블
                        'parents': row['topic_category'],
                        'values': row['post_count'],
                        'cluster_name': cluster_name,  # 원본 클러스터명 저장
                        'display_text': display_text  # 표시용 텍스트
                    })
                
                # 카테고리 레벨 추가 (중복 제거)
                unique_categories = dist_df['topic_category'].unique()
                for cat in unique_categories:
                    treemap_data.append({
                        'labels': cat,
                        'parents': '',
                        'values': 0,  # 자동 계산됨
                        'display_text': cat
                    })
                
                # DataFrame 생성 및 정리
                treemap_df = pd.DataFrame(treemap_data)
                # 카테고리 레벨의 values는 자식들의 합으로 계산
                category_totals = treemap_df[treemap_df['parents'] != ''].groupby('parents')['values'].sum()
                for cat in category_totals.index:
                    treemap_df.loc[
                        (treemap_df['labels'] == cat) & (treemap_df['parents'] == ''),
                        'values'
                    ] = category_totals[cat]
                
                # Treemap 생성 (커스텀 hover 템플릿)
                # hover 템플릿을 위한 데이터 준비
                hover_texts = []
                # 카테고리별 총합 계산
                category_totals_dict = {}
                for cat in unique_categories:
                    cat_total = dist_df[dist_df['topic_category'] == cat]['post_count'].sum()
                    category_totals_dict[cat] = cat_total
                
                for idx, row in treemap_df.iterrows():
                    parent = row['parents']
                    value = row['values']
                    
                    if row.get('cluster_name') and row['cluster_name'] in keywords_map:
                        cluster_name = row['cluster_name']
                        keywords = keywords_map.get(cluster_name, "")
                        summary = summary_map.get(cluster_name, "")
                        
                        # 비중 계산
                        if parent and parent in category_totals_dict and category_totals_dict[parent] > 0:
                            percent = (value / category_totals_dict[parent]) * 100
                            hover_text = f"<b>{cluster_name}</b><br>"
                            hover_text += f"포스트: {value}개 | 비중: {percent:.1f}%<br>"
                            if keywords:
                                # 키워드를 한 줄로 표시 (최대 10개)
                                keywords_list = keywords.split(', ')[:10]
                                keywords_short = ', '.join(keywords_list)
                                hover_text += f"키워드: {keywords_short}"
                                if len(keywords.split(', ')) > 10:
                                    hover_text += "..."
                            if summary:
                                # 요약을 한 줄로 표시 (최대 80자)
                                summary_short = summary[:80] + '...' if len(summary) > 80 else summary
                                hover_text += f"<br>요약: {summary_short}"
                        else:
                            hover_text = f"<b>{cluster_name}</b><br>"
                            hover_text += f"포스트: {value}개<br>"
                            if keywords:
                                keywords_list = keywords.split(', ')[:10]
                                keywords_short = ', '.join(keywords_list)
                                hover_text += f"키워드: {keywords_short}"
                                if len(keywords.split(', ')) > 10:
                                    hover_text += "..."
                            if summary:
                                summary_short = summary[:80] + '...' if len(summary) > 80 else summary
                                hover_text += f"<br>요약: {summary_short}"
                    else:
                        # 카테고리 레벨
                        hover_text = f"<b>{row['labels']}</b><br>포스트: {value}개"
                    hover_texts.append(hover_text)
                
                fig_treemap = go.Figure(go.Treemap(
                    labels=treemap_df['labels'].tolist(),
                    parents=treemap_df['parents'].tolist(),
                    values=treemap_df['values'].tolist(),
                    branchvalues="total",
                    hovertemplate='%{hovertext}<extra></extra>',
                    hovertext=hover_texts,
                    text=treemap_df['display_text'].tolist(),  # 커스텀 텍스트 (클러스터명 + 키워드)
                    textinfo="text",  # 커스텀 텍스트만 표시
                    textfont=dict(size=11),
                    textposition="middle center",
                    marker=dict(
                        colorscale='Viridis',
                        cmid=treemap_df['values'].median(),
                        line=dict(width=2, color='white')  # 구분선 추가
                    )
                ))
                
                fig_treemap.update_layout(
                    height=700,
                    title="카테고리별 클러스터 비중",
                    font=dict(size=12),
                    margin=dict(l=10, r=10, t=50, b=10)
                )
                
                st.plotly_chart(fig_treemap, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ 시각화 데이터를 불러오는 중 오류가 발생했습니다: {e}")
            import traceback
            traceback.print_exc()
        
        st.markdown("---")
        
        # 카테고리 필터
        categories = clusters_df['topic_category'].dropna().unique()
        available_categories = sorted([cat for cat in categories if pd.notna(cat)])
        
        if available_categories:
            selected_category = st.selectbox(
                "카테고리 선택",
                ["All"] + available_categories,
                key="cluster_category_filter"
            )
            
            # 필터링
            if selected_category == "All":
                filtered_df = clusters_df[clusters_df['topic_category'].notna()]
            else:
                filtered_df = clusters_df[clusters_df['topic_category'] == selected_category]
            
            # 클러스터 표시
            for idx, (_, cluster_row) in enumerate(filtered_df.iterrows()):
                cluster_id = cluster_row['cluster_id']
                cluster_id_str = str(cluster_id)
                cluster_name = cluster_row.get('cluster_name', f"Cluster_{cluster_id}")
                topic_category = cluster_row.get('topic_category')
                
                if pd.isna(topic_category) or topic_category is None:
                    topic_category_display = 'Unknown'
                else:
                    topic_category_display = topic_category
                
                size = cluster_row.get('size', 0)
                sub_cluster_index = cluster_row.get('sub_cluster_index')
                top_keywords = cluster_row.get('top_keywords', [])
                if not isinstance(top_keywords, list):
                    top_keywords = []
                
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
                    
                    # 요약 표시 (JSON의 summary 우선, GPT 요약은 선택적)
                    summary = cluster_row.get('summary', '')
                    if summary:
                        st.markdown("**📝 요약:**")
                        st.info(summary)
                    
                    # GPT 요약 (선택적, JSON summary가 없거나 추가 요약이 필요한 경우)
                    try:
                        if is_openai_available() and st.checkbox("GPT로 추가 요약 생성", key=f"gpt_summary_{cluster_id_str}"):
                            with st.spinner("GPT로 클러스터 요약 생성 중..."):
                                gpt_summary = gpt_service.generate_cluster_summary(
                                    cluster_id_str,
                                    top_keywords[:10] if top_keywords else [],
                                    int(size),
                                    topic_category_display if topic_category_display != 'Unknown' else 'Unknown'
                                )
                                if gpt_summary:
                                    st.markdown("**🤖 GPT 요약:**")
                                    st.success(gpt_summary)
                                else:
                                    st.info("요약을 생성할 수 없습니다.")
                    except Exception as gpt_error:
                        # GPT 실패 시 에러 메시지 표시 (조용히 실패)
                        pass
                    
                    # Top Keywords
                    if top_keywords:
                        st.markdown("**🔑 주요 키워드:**")
                        keywords_str = ", ".join(top_keywords[:20])
                        st.write(keywords_str)
                        if len(top_keywords) > 20:
                            st.caption(f"총 {len(top_keywords)}개 키워드 중 상위 20개 표시")
        else:
            st.info("Not available")
            
    except Exception as e:
        st.error(f"Error loading clustering results: {e}")
        st.info("Not available")


