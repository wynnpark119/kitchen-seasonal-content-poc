"""
Master Topics 뷰

마스터 토픽 결과 표시
"""
import streamlit as st
import json
import time
import re
from pathlib import Path


def parse_master_topics(markdown_text):
    """
    마스터 토픽 마크다운 텍스트를 구조화된 데이터로 파싱
    
    Args:
        markdown_text: 마크다운 형식의 텍스트
        
    Returns:
        List[Dict]: 각 항목은 {'title': str, 'why_now': str} 형태
    """
    if not markdown_text:
        return []
    
    items = []
    lines = markdown_text.split('\n')
    current_title = None
    current_why_now = []
    in_why_now = False
    
    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        # 빈 줄 처리
        if not line:
            if in_why_now and current_title:
                # Why now 섹션 내의 빈 줄은 공백으로 추가 (줄바꿈 유지)
                current_why_now.append(' ')
            continue
        
        # 번호가 있는 항목 시작 (예: "1) **제목**" 또는 "1) 제목")
        title_patterns = [
            r'^\d+\)\s*\*\*(.+?)\*\*',  # 1) **제목**
            r'^\d+\)\s*(.+?)$',          # 1) 제목
        ]
        
        title_match = None
        for pattern in title_patterns:
            title_match = re.match(pattern, line)
            if title_match:
                break
        
        if title_match:
            # 이전 항목 저장
            if current_title:
                why_now_text = '\n'.join(current_why_now).strip()
                # 연속된 공백/줄바꿈 정리
                why_now_text = re.sub(r'\s+', ' ', why_now_text)
                why_now_text = re.sub(r'\n\s*\n', '\n', why_now_text)
                items.append({
                    'title': current_title,
                    'why_now': why_now_text
                })
            
            # 새 항목 시작
            current_title = title_match.group(1).strip()
            # 마크다운 제거
            current_title = re.sub(r'\*\*([^*]+)\*\*', r'\1', current_title)
            current_title = re.sub(r'`([^`]+)`', r'\1', current_title)
            current_why_now = []
            in_why_now = False
            continue
        
        # "Why now:" 패턴 (다양한 형식 지원)
        why_now_patterns = [
            r'^[-*]?\s*\*\*Why now:\*\*\s*(.*)',  # - **Why now:** 텍스트
            r'^[-*]?\s*\*\*Why now\*\*:\s*(.*)',  # - **Why now**: 텍스트
            r'^[-*]?\s*Why now:\s*(.*)',           # - Why now: 텍스트
            r'^\*\*Why now:\*\*\s*(.*)',           # **Why now:** 텍스트
        ]
        
        matched = False
        for pattern in why_now_patterns:
            why_now_match = re.match(pattern, line, re.IGNORECASE)
            if why_now_match:
                in_why_now = True
                why_now_text = why_now_match.group(1).strip()
                if why_now_text:
                    # 마크다운 제거
                    why_now_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', why_now_text)
                    why_now_text = re.sub(r'`([^`]+)`', r'\1', why_now_text)
                    current_why_now.append(why_now_text)
                matched = True
                break
        
        if matched:
            continue
        
        # Why now 섹션 내의 텍스트 (다음 번호 항목이 나올 때까지)
        if in_why_now and current_title:
            # 다음 번호 항목이 시작되면 Why now 종료
            if re.match(r'^\d+\)', line):
                # 이전 항목 저장하고 새 항목 시작
                why_now_text = '\n'.join(current_why_now).strip()
                why_now_text = re.sub(r'\s+', ' ', why_now_text)
                items.append({
                    'title': current_title,
                    'why_now': why_now_text
                })
                # 새 항목 파싱
                title_match = None
                for pattern in title_patterns:
                    title_match = re.match(pattern, line)
                    if title_match:
                        break
                if title_match:
                    current_title = title_match.group(1).strip()
                    current_title = re.sub(r'\*\*([^*]+)\*\*', r'\1', current_title)
                    current_why_now = []
                    in_why_now = False
                continue
            
            # 마크다운 제거
            clean_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            clean_line = re.sub(r'`([^`]+)`', r'\1', clean_line)
            clean_line = clean_line.strip()
            if clean_line:
                current_why_now.append(clean_line)
    
    # 마지막 항목 저장
    if current_title:
        why_now_text = '\n'.join(current_why_now).strip()
        why_now_text = re.sub(r'\s+', ' ', why_now_text)
        items.append({
            'title': current_title,
            'why_now': why_now_text
        })
    
    return items


def clean_markdown(markdown_text):
    """
    마크다운 텍스트에서 불필요한 구분선 제거
    
    Args:
        markdown_text: 마크다운 형식의 텍스트
        
    Returns:
        정리된 마크다운 텍스트
    """
    if not markdown_text:
        return ""
    
    text = markdown_text
    
    # ===== 같은 구분선 제거
    text = re.sub(r'=+\s*\n', '', text)
    text = re.sub(r'\n\s*=+', '', text)
    text = re.sub(r'=+', '', text)
    
    # ------- 같은 구분선 제거
    text = re.sub(r'-+\s*\n', '', text)
    text = re.sub(r'\n\s*-+', '', text)
    text = re.sub(r'^-+$', '', text, flags=re.MULTILINE)
    
    # 빈 줄 정리 (3개 이상 연속된 빈 줄을 2개로)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text


def render_master_topics():
    """Master Topics 탭 렌더링"""
    topic_categories = [
        "SPRING_RECIPES",
        "REFRIGERATOR_ORGANIZATION",
        "VEGETABLE_PREP_HANDLING",
        "SPRING_KITCHEN_STYLING"
    ]
    
    # 저장된 결과 파일 경로
    project_root = Path(__file__).parent.parent.parent
    master_topics_file = project_root / "data" / "master_topics.json"
    
    # 1초 로딩 표시
    with st.spinner("마스터 토픽을 불러오는 중..."):
        time.sleep(1)
    
    # 저장된 결과 로드
    saved_results = {}
    if master_topics_file.exists():
        try:
            with open(master_topics_file, 'r', encoding='utf-8') as f:
                saved_results = json.load(f)
        except Exception as e:
            st.error(f"Error loading master topics file: {e}")
            st.info("Not available")
            return
    else:
        st.info("Not available")
        return
    
    # 결과 표시 (구조화된 형태로 파싱하여 표시)
    if saved_results:
        for idx, topic_category in enumerate(topic_categories):
            # 카테고리별 expander 사용
            with st.expander(f"📌 {topic_category}", expanded=True):
                if topic_category in saved_results:
                    markdown_content = saved_results[topic_category]
                    
                    # 마스터 토픽 파싱 시도
                    parsed_items = parse_master_topics(markdown_content)
                    
                    if parsed_items and len(parsed_items) > 0:
                        # 파싱 성공: 구조화된 형태로 표시
                        for item_idx, item in enumerate(parsed_items, start=1):
                            # 제목
                            st.markdown(f"**{item_idx}. {item['title']}**")
                            
                            # Why now
                            if item['why_now']:
                                st.markdown(f"**Why now:** {item['why_now']}")
                            else:
                                st.markdown("**Why now:** (내용 없음)")
                            
                            # 항목 간 구분선
                            if item_idx < len(parsed_items):
                                st.markdown("---")
                    else:
                        # 파싱 실패: 구분선만 제거하고 표시
                        cleaned_content = clean_markdown(markdown_content)
                        if cleaned_content:
                            # 파싱 실패 경고와 함께 원문 일부 표시
                            st.warning("⚠️ 파싱에 실패했습니다. 원문을 표시합니다.")
                            st.markdown(cleaned_content[:500] + ("..." if len(cleaned_content) > 500 else ""))
                        else:
                            st.info("내용이 없습니다.")
                else:
                    st.info("Not available")
        
        # 전체 결과 다운로드
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
        st.info("Not available")
