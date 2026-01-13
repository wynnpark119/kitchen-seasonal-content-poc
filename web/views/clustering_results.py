"""
Clustering Results 뷰

클러스터링 결과 표시
"""
import streamlit as st
import pandas as pd
import importlib
import sys
import logging

# 모듈 재로드를 위해 import
from services import clustering_service
from services.gpt_service import get_gpt_service
from common.openai_client import is_openai_available

# 로거 설정
logger = logging.getLogger(__name__)

# Streamlit 모듈 캐싱 문제 해결: 모듈 재로드
if 'services.clustering_service' in sys.modules:
    importlib.reload(clustering_service)


def render_cluster_detail(cluster_row: pd.Series, gpt_service):
    """클러스터 상세 정보 렌더링"""
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
    
    # 요약 표시 (Cluster ID와 Size 메트릭 제거)
    summary = cluster_row.get('summary', '')
    if summary:
        st.markdown("**클러스터 개요**")
        st.caption(summary)
    
    # GPT 요약 (선택적)
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
        st.markdown("**주요 키워드**")
        keywords_str = ", ".join(top_keywords[:20])
        st.caption(keywords_str)
        if len(top_keywords) > 20:
            st.caption(f"총 {len(top_keywords)}개 키워드 중 상위 20개 표시")


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
        
        # 카테고리별로 그룹화
        categories = clusters_df['topic_category'].dropna().unique()
        available_categories = sorted([cat for cat in categories if pd.notna(cat)])
        
        if not available_categories:
            st.info("카테고리 데이터가 없습니다.")
            return
        
        # 카테고리 필터 드롭박스
        category_labels = {cat: cat.replace("_", " ").title() for cat in available_categories}
        category_options = [category_labels[cat] for cat in available_categories]
        
        # 세션 상태에서 선택된 카테고리 가져오기 (없으면 첫 번째 카테고리)
        if 'selected_category' not in st.session_state:
            st.session_state.selected_category = available_categories[0]
        
        # 필터 2개를 횡으로 배치 (상단에 나란히 배치)
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # 드롭박스로 카테고리 선택
            selected_category_label = st.selectbox(
                "카테고리 선택",
                category_options,
                index=available_categories.index(st.session_state.selected_category) if st.session_state.selected_category in available_categories else 0,
                key="category_filter"
            )
            
            # 선택된 라벨에 해당하는 카테고리 찾기
            selected_category = None
            for cat, label in category_labels.items():
                if label == selected_category_label:
                    selected_category = cat
                    break
            
            if selected_category is None:
                selected_category = available_categories[0]
            
            st.session_state.selected_category = selected_category
        
        with filter_col2:
            # 클러스터 필터 (선택된 카테고리가 변경되면 클러스터 목록도 업데이트)
            if selected_category != st.session_state.get('prev_category', None):
                # 카테고리가 변경되면 첫 번째 클러스터 선택
                st.session_state.selected_cluster_name = None
                st.session_state.prev_category = selected_category
            
            # 선택된 카테고리의 클러스터 필터링
            filtered_df = clusters_df[clusters_df['topic_category'] == selected_category]
            
            # 클러스터 목록 생성
            cluster_list = []
            for idx, (_, cluster_row) in enumerate(filtered_df.iterrows()):
                cluster_name = cluster_row.get('cluster_name')
                if not cluster_name or pd.isna(cluster_name):
                    topic_category = cluster_row.get('topic_category')
                    sub_cluster_index = cluster_row.get('sub_cluster_index')
                    if pd.notna(sub_cluster_index):
                        cluster_name = f"{topic_category}_{int(sub_cluster_index) + 1}"
                    else:
                        cluster_name = f"Cluster_{cluster_row.get('cluster_id', idx)}"
                
                cluster_list.append({
                    'name': cluster_name,
                    'row': cluster_row
                })
            
            if len(cluster_list) == 0:
                st.selectbox(
                    "클러스터 선택",
                    ["클러스터 없음"],
                    key="cluster_filter",
                    disabled=True
                )
            else:
                cluster_names = [c['name'] for c in cluster_list]
                
                # 세션 상태에서 선택된 클러스터 가져오기
                if 'selected_cluster_name' not in st.session_state or st.session_state.selected_cluster_name not in cluster_names:
                    st.session_state.selected_cluster_name = cluster_names[0]
                
                selected_cluster_name = st.selectbox(
                    "클러스터 선택",
                    cluster_names,
                    index=cluster_names.index(st.session_state.selected_cluster_name) if st.session_state.selected_cluster_name in cluster_names else 0,
                    key="cluster_filter"
                )
                
                st.session_state.selected_cluster_name = selected_cluster_name
        
        st.markdown("---")
        st.markdown(
            """
            <style>
            /* 설명문(caption)과 첫 번째 탭 사이 간격 50% 축소 - 더 강력한 선택자 */
            [data-testid="stCaption"] {
                margin-bottom: 0.25rem !important;
            }
            
            /* 첫 번째 탭 그룹의 상단 여백 축소 */
            [data-testid="stTabs"]:first-of-type {
                margin-top: 0.25rem !important;
            }
            
            /* 모든 탭 텍스트 크기 통일 */
            [data-testid="stTabs"] button[role="tab"],
            [data-testid="stTabs"] button[role="tab"] *,
            [data-testid="stTabs"] button[role="tab"] div,
            [data-testid="stTabs"] button[role="tab"] span {
                font-size: 0.95rem !important;
                font-weight: 500 !important;
                color: #9E9E9E !important;
                padding: 8px 16px !important;
                background-color: transparent !important;
            }
            
            /* 모든 탭 active 상태 - 기본 Streamlit 스타일 유지 (green 언더바 제거) */
            [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
                color: #ffffff !important;
                background-color: transparent !important;
            }
            
            /* 비활성 탭은 border 제거 */
            [data-testid="stTabs"] button[role="tab"]:not([aria-selected="true"]) {
                border-bottom: none !important;
            }
            
            /* 주제 탭과 클러스터 세부 탭 간격 */
            [data-testid="stTabs"]:first-of-type {
                margin-bottom: 3rem !important;
            }
            
            /* 클러스터 탭 (두 번째 레벨) 스타일 - 원래대로 복구 (배경 없이 언더라인만) */
            /* 상단 탭 스타일의 영향을 받지 않도록 명시적으로 원래 크기 강제 */
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"],
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"] *,
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"] div,
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"] span,
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"] p {
                font-size: 0.95rem !important;
                font-weight: 500 !important;
                color: #9E9E9E !important;
                padding: 8px 16px !important;
                background-color: transparent !important;
                border-bottom: none !important; /* 우리가 추가한 border 제거 */
            }
            
            /* 클러스터 탭 active - 배경 없이 기본 red 언더라인만 (Streamlit 기본 스타일 유지) */
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
                color: #ffffff !important;
                background-color: transparent !important;
                background: transparent !important;
                font-weight: 600 !important;
                border-bottom: none !important; /* 우리가 추가한 border 제거 - Streamlit 기본 언더라인만 사용 */
            }
            
            /* 클러스터 탭의 green 언더라인 완전 제거 */
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"],
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {
                background-color: transparent !important;
                background: transparent !important;
                border-bottom: none !important; /* 우리가 추가한 border 제거 */
            }
            
            /* 클러스터 탭의 ::after, ::before pseudo-element border 제거 */
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"]::after,
            [data-testid="stTabs"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"]::before {
                border-bottom: none !important;
                background-color: transparent !important;
            }
            
            /* 클러스터 탭의 tablist 내부 요소 border 제거 */
            [data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"] button[aria-selected="true"] {
                border-bottom: none !important; /* 우리가 추가한 border 제거 */
                background-color: transparent !important;
            }
            
            /* 클러스터 탭 간격 */
            [data-testid="stTabs"] [data-testid="stTabs"] {
                margin-top: 0.5rem !important;
                margin-bottom: 1rem !important;
            }
            </style>
            <script>
            // 동적으로 스타일 적용 (MutationObserver 사용)
            (function() {
                function applyStyles() {
                    const tabs = document.querySelectorAll('[data-testid="stTabs"]');
                    if (tabs.length > 0) {
                        // 모든 탭을 동일한 스타일로 통일
                        tabs.forEach((tab, tabIndex) => {
                            const tabList = tab.querySelector('[role="tablist"]');
                            if (tabList) {
                                const buttons = tabList.querySelectorAll('button[role="tab"]');
                                buttons.forEach(btn => {
                                    // 모든 탭 텍스트 크기 통일
                                    btn.style.fontSize = '0.95rem';
                                    btn.style.fontWeight = '500';
                                    btn.style.padding = '8px 16px';
                                    btn.style.backgroundColor = 'transparent';
                                    
                                    // 버튼 내부의 모든 텍스트 요소에도 동일한 스타일 적용
                                    const textElements = btn.querySelectorAll('*');
                                    textElements.forEach(el => {
                                        el.style.fontSize = '0.95rem';
                                        el.style.fontWeight = '500';
                                    });
                                    
                                    // 우리가 추가한 green border 제거
                                    if (btn.style.borderBottom && btn.style.borderBottom.includes('#4CAF50')) {
                                        btn.style.borderBottom = 'none';
                                    }
                                    if (btn.style.borderBottomColor && btn.style.borderBottomColor.includes('#4CAF50')) {
                                        btn.style.borderBottom = 'none';
                                    }
                                    
                                    if (btn.getAttribute('aria-selected') === 'true') {
                                        btn.style.color = '#ffffff';
                                        // Streamlit 기본 언더라인만 사용 (우리가 추가한 border 제거)
                                        btn.style.borderBottom = 'none';
                                    } else {
                                        btn.style.color = '#9E9E9E';
                                        btn.style.borderBottom = 'none';
                                    }
                                });
                                
                                // tabList 내부의 모든 요소에서 green border 제거
                                const allElements = tabList.querySelectorAll('*');
                                allElements.forEach(el => {
                                    const style = window.getComputedStyle(el);
                                    // green 계열의 border 제거
                                    if (style.borderBottomColor && (
                                        style.borderBottomColor.includes('4CAF50') ||
                                        style.borderBottomColor.includes('76, 175, 80')
                                    )) {
                                        el.style.borderBottom = 'none';
                                    }
                                    // background가 green 계열이면 transparent로
                                    if (style.backgroundColor && (
                                        style.backgroundColor.includes('4CAF50') ||
                                        style.backgroundColor.includes('76, 175, 80')
                                    )) {
                                        el.style.backgroundColor = 'transparent';
                                    }
                                });
                            }
                        });
                    }
                }
                
                // 즉시 실행
                applyStyles();
                
                // 모든 탭의 green 언더라인 제거 함수
                function updateUnderlineColor() {
                    // 모든 탭에서 green 언더라인 제거
                    const allTabs = document.querySelectorAll('[data-testid="stTabs"]');
                    allTabs.forEach(tab => {
                        const tabList = tab.querySelector('[role="tablist"]');
                        if (tabList) {
                            const buttons = tabList.querySelectorAll('button[role="tab"]');
                            buttons.forEach(btn => {
                                // 우리가 추가한 green border 제거
                                if (btn.style.borderBottom && btn.style.borderBottom.includes('#4CAF50')) {
                                    btn.style.borderBottom = 'none';
                                }
                                if (btn.style.borderBottomColor && btn.style.borderBottomColor.includes('#4CAF50')) {
                                    btn.style.borderBottom = 'none';
                                }
                                btn.style.backgroundColor = 'transparent';
                            });
                            
                            // tabList 내부의 모든 요소에서 green border 제거
                            const allElements = tabList.querySelectorAll('*');
                            allElements.forEach(el => {
                                const style = window.getComputedStyle(el);
                                // green 계열의 border 제거
                                if (style.borderBottomColor && (
                                    style.borderBottomColor.includes('4CAF50') ||
                                    style.borderBottomColor.includes('76, 175, 80')
                                )) {
                                    el.style.borderBottom = 'none';
                                }
                                // background가 green 계열이면 transparent로
                                if (style.backgroundColor && (
                                    style.backgroundColor.includes('4CAF50') ||
                                    style.backgroundColor.includes('76, 175, 80')
                                )) {
                                    el.style.backgroundColor = 'transparent';
                                }
                            });
                        }
                    });
                }
                
                // DOM 변경 감지
                const observer = new MutationObserver(function(mutations) {
                    applyStyles();
                    updateUnderlineColor();
                });
                
                // 문서 로드 후 observer 시작
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true,
                            attributes: true,
                            attributeFilter: ['aria-selected']
                        });
                        setTimeout(function() {
                            applyStyles();
                            updateUnderlineColor();
                        }, 100);
                    });
                } else {
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        attributeFilter: ['aria-selected']
                    });
                    setTimeout(function() {
                        applyStyles();
                        updateUnderlineColor();
                    }, 100);
                }
                
                // 추가 안전장치: 여러 번 시도
                setTimeout(function() {
                    applyStyles();
                    updateUnderlineColor();
                }, 200);
                setTimeout(function() {
                    applyStyles();
                    updateUnderlineColor();
                }, 500);
                setTimeout(function() {
                    applyStyles();
                    updateUnderlineColor();
                }, 1000);
            })();
            </script>
            """,
            unsafe_allow_html=True
        )
        
        # 선택된 클러스터 표시
        if len(cluster_list) == 0:
            st.info("이 카테고리에 해당하는 클러스터가 없습니다.")
            return
        
        # 선택된 클러스터 찾기 및 표시
        selected_cluster = next((c for c in cluster_list if c['name'] == selected_cluster_name), None)
        
        if selected_cluster:
            render_cluster_detail(selected_cluster['row'], gpt_service)
        else:
            st.warning("클러스터를 찾을 수 없습니다.")
            
    except Exception as e:
        st.error(f"Error loading clustering results: {e}")
        import traceback
        with st.expander("상세 오류 보기"):
            st.code(traceback.format_exc())
        st.info("Not available")
