"""
마스터 토픽 생성 스크립트 (콘솔 출력용)

목적: Reddit 클러스터링 결과 + SERP 질문형 키워드를 기반으로
      GPT가 생성한 마스터 토픽을 콘솔에 출력

사용법:
    python generate_master_topics_console.py
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    # dotenv가 없으면 .env 파일을 직접 읽기
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

from web.db_queries import (
    get_reddit_clustering_for_master_topic,
    get_serp_questions_for_master_topic
)
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError
from typing import List, Dict, Any, Optional

# OpenAI 클라이언트 통합 모듈 사용
from common.openai_client import get_openai_client

# Topic Categories
TOPIC_CATEGORIES = [
    "SPRING_RECIPES",
    "REFRIGERATOR_ORGANIZATION",
    "VEGETABLE_PREP_HANDLING",
    "SPRING_KITCHEN_STYLING"
]

def format_reddit_clusters_for_prompt(clusters: List[Dict[str, Any]]) -> str:
    """Reddit 클러스터링 결과를 프롬프트용 텍스트로 포맷팅"""
    if not clusters:
        return "Reddit 클러스터링 데이터 없음"
    
    formatted = []
    for cluster in clusters:
        cluster_info = f"""
- Cluster ID: {cluster.get('cluster_id', 'N/A')}
- Sub Cluster ID: {cluster.get('sub_cluster_id', 'N/A')}
- Cluster Size: {cluster.get('cluster_size', 0)}
- Top Keywords: {', '.join(cluster.get('top_keywords', [])[:15])}
- Summary: {cluster.get('summary', 'N/A')}
"""
        # 대표 포스트 제목 추가
        rep_posts = cluster.get('representative_posts', [])
        if rep_posts:
            cluster_info += "- 대표 포스트 제목:\n"
            for post in rep_posts[:3]:
                title = post.get('title', 'N/A')
                cluster_info += f"  * {title}\n"
        formatted.append(cluster_info)
    
    return "\n".join(formatted)

def format_serp_questions_for_prompt(questions: List[str]) -> str:
    """SERP 질문형 키워드를 프롬프트용 텍스트로 포맷팅"""
    if not questions:
        return "SERP 질문형 키워드 없음"
    
    return "\n".join([f"- {q}" for q in questions[:100]])

def generate_master_topics_for_category(
    topic_category: str,
    reddit_clusters: List[Dict[str, Any]],
    serp_questions: List[str],
    client
) -> Optional[str]:
    """특정 topic_category에 대한 마스터 토픽 생성"""
    
    # Reddit 클러스터링 결과 포맷팅
    reddit_text = format_reddit_clusters_for_prompt(reddit_clusters)
    
    # SERP 질문형 키워드 포맷팅
    serp_text = format_serp_questions_for_prompt(serp_questions)
    
    # GPT 프롬프트
    prompt = f"""너는 데이터 기반 콘텐츠 전략가다.

입력으로 제공되는 정보는 두 가지다.
1) Reddit 클러스터링 결과: 지금 사람들이 실제로 겪는 문제와 관심사
2) SERP 질문형 키워드: 지금 사람들이 검색창에 직접 입력하는 질문

이 두 신호를 결합해,
LG전자 블로그/소셜에서 "지금 이 시점에" 다뤄야 할
마스터 토픽을 도출하라.

중요 기준:
- 각 topic_category별로 정확히 5개의 마스터 토픽만 생성한다.
- 각 마스터 토픽에는 반드시 Why now를 포함한다.
- Why now는 다음 두 요소를 반드시 연결해 설명한다:
  (1) Reddit 클러스터에서 관찰된 사용자 맥락/불편/욕구
  (2) SERP 질문형 키워드에서 나타난 검색 의도 패턴

추상적인 표현("트렌드다", "중요하다")은 금지한다.
계절 변화, 행동 변화, 반복 질문, 문제 전환 등
'지금 시점성'을 논리적으로 설명하라.

[입력 데이터]

Topic Category: {topic_category}

[Reddit 클러스터링 결과]
{reddit_text}

[SERP 질문형 키워드]
{serp_text}

[출력 포맷 — 반드시 이 형식으로만 출력]

==============================
## {topic_category}
==============================

1) **{{마스터 토픽 제목}}**
- Why now: {{2~3문장}}

2) **{{마스터 토픽 제목}}**
- Why now: {{2~3문장}}

3) **{{마스터 토픽 제목}}**
- Why now: {{2~3문장}}

4) **{{마스터 토픽 제목}}**
- Why now: {{2~3문장}}

5) **{{마스터 토픽 제목}}**
- Why now: {{2~3문장}}

[검증]
- topic_category는 반드시 {topic_category}만 사용
- 정확히 5개인지 확인
- 모든 항목에 Why now가 있는지 확인
- Reddit/SERP 신호가 섞여 설명되고 있는지 확인

이 조건을 만족하지 않으면 재생성하라."""

    try:
        print(f"  🤖 GPT API 호출 중... ({topic_category})")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a data-driven content strategist specializing in creating master topics for LG Electronics blog and social media content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        result = response.choices[0].message.content.strip()
        return result
    except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
        print(f"  ❌ GPT API 호출 오류: {e}")
        return None
    except Exception as e:
        print(f"  ❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def validate_master_topics_output(output: str, topic_category: str) -> bool:
    """마스터 토픽 출력 검증"""
    if not output:
        return False
    
    # topic_category가 포함되어 있는지 확인
    if topic_category not in output:
        return False
    
    # "Why now"가 5번 나타나는지 확인
    why_now_count = output.count("Why now:")
    if why_now_count != 5:
        return False
    
    # 번호가 1)부터 5)까지 있는지 확인
    for i in range(1, 6):
        if f"{i})" not in output:
            return False
    
    return True

def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("GPT 마스터 토픽 생성 시작")
    print("=" * 70)
    print()
    
    # OpenAI 클라이언트 확인
    try:
        client = get_openai_client()
        print("✅ OpenAI API 클라이언트 초기화 완료")
        print()
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    
    # 각 topic_category별로 처리
    all_results = {}
    
    for topic_category in TOPIC_CATEGORIES:
        print(f"📊 처리 중: {topic_category}")
        print("-" * 70)
        
        # 1. Reddit 클러스터링 결과 조회
        print(f"  📥 Reddit 클러스터링 데이터 조회 중...")
        reddit_clusters = get_reddit_clustering_for_master_topic(topic_category)
        
        if not reddit_clusters:
            print(f"  ⚠️  경고: {topic_category}에 대한 Reddit 클러스터링 데이터를 찾을 수 없습니다.")
        else:
            print(f"  ✅ Reddit 클러스터 {len(reddit_clusters)}개 조회됨")
        
        # 2. SERP 질문형 키워드 조회
        print(f"  📥 SERP 질문형 키워드 조회 중...")
        serp_questions = get_serp_questions_for_master_topic(topic_category)
        
        if not serp_questions:
            print(f"  ⚠️  경고: {topic_category}에 대한 SERP 질문형 키워드를 찾을 수 없습니다.")
        else:
            print(f"  ✅ SERP 질문형 키워드 {len(serp_questions)}개 조회됨")
        
        # 3. GPT로 마스터 토픽 생성
        if not reddit_clusters and not serp_questions:
            print(f"  ❌ 데이터가 없어 {topic_category}를 건너뜁니다.")
            print()
            continue
        
        master_topics_result = generate_master_topics_for_category(
            topic_category,
            reddit_clusters,
            serp_questions,
            client
        )
        
        if not master_topics_result:
            print(f"  ❌ {topic_category}에 대한 마스터 토픽 생성 실패")
            print()
            continue
        
        # 4. 검증
        if not validate_master_topics_output(master_topics_result, topic_category):
            print(f"  ⚠️  검증 실패: {topic_category} 결과를 재생성합니다...")
            # 재시도 (최대 1회)
            master_topics_result = generate_master_topics_for_category(
                topic_category,
                reddit_clusters,
                serp_questions,
                client
            )
            if master_topics_result and validate_master_topics_output(master_topics_result, topic_category):
                print(f"  ✅ 재생성 성공")
            else:
                print(f"  ⚠️  재생성 후에도 검증 실패 (그대로 출력)")
        
        all_results[topic_category] = master_topics_result
        print(f"  ✅ {topic_category} 완료")
        print()
    
    # 결과를 파일로 저장
    import json
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    master_topics_file = data_dir / "master_topics.json"
    
    if all_results:
        try:
            with open(master_topics_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 마스터 토픽 결과가 저장되었습니다: {master_topics_file}")
        except Exception as save_error:
            print(f"\n❌ 결과 저장 중 오류 발생: {save_error}")
    
    # 결과 출력
    print()
    print("=" * 70)
    print("생성된 마스터 토픽 결과")
    print("=" * 70)
    print()
    
    for i, topic_category in enumerate(TOPIC_CATEGORIES):
        if topic_category in all_results:
            result = all_results[topic_category]
            print(result)
            
            # 마지막 카테고리가 아니면 빈 줄 2개 추가
            if i < len(TOPIC_CATEGORIES) - 1:
                print()
                print()
        else:
            print(f"## {topic_category}")
            print("(데이터 없음으로 인해 생성되지 않음)")
            if i < len(TOPIC_CATEGORIES) - 1:
                print()
                print()
    
    print()
    print("=" * 70)
    print("=== GPT 마스터 토픽 생성 완료 ===")
    print("=" * 70)
    if all_results:
        print(f"💾 결과 파일: {master_topics_file}")
        print("   Streamlit 대시보드에서 이 파일을 자동으로 읽어 표시합니다.")

if __name__ == "__main__":
    main()
