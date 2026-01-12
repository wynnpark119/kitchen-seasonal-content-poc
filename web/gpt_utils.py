"""
GPT API 호출 유틸리티
실시간으로 GPT 응답을 받아서 표시
"""
import os
from typing import Optional, Dict, Any
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError

def get_openai_client() -> Optional[OpenAI]:
    """OpenAI 클라이언트 생성"""
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return None
    return OpenAI(api_key=openai_key)

def generate_monthly_trend_summary(timeseries_df, cluster_name: str, category: str) -> Optional[str]:
    """월간 트렌드 데이터를 기반으로 GPT 요약 생성"""
    client = get_openai_client()
    if not client:
        return None
    
    # 시계열 데이터를 텍스트로 변환
    trend_data = timeseries_df.to_string(index=False) if len(timeseries_df) > 0 else "No data available"
    
    prompt = f"""다음은 클러스터 '{cluster_name}' ({category})의 월간 트렌드 데이터입니다.

트렌드 데이터:
{trend_data}

이 데이터를 분석하여 다음을 포함한 간단한 요약을 작성해주세요:
1. 전반적인 트렌드 (증가/감소/안정)
2. 주요 변화 시점
3. 시즌성 패턴 (있는 경우)

한국어로 간결하게 작성해주세요 (3-5문장)."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data analyst specializing in trend analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
        print(f"Error calling GPT API for monthly trend: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in generate_monthly_trend_summary: {e}")
        return None

def generate_representative_posts_summary(rep_posts_df, cluster_name: str) -> Optional[str]:
    """대표 포스트 데이터를 기반으로 GPT 요약 생성"""
    client = get_openai_client()
    if not client:
        return None
    
    # 대표 포스트 정보를 텍스트로 변환
    posts_summary = []
    for idx, row in rep_posts_df.head(5).iterrows():  # 상위 5개만 사용
        posts_summary.append(f"- {row.get('title', 'N/A')} (↑{row.get('upvotes', 0)}, 💬{row.get('num_comments', 0)})")
    
    posts_text = "\n".join(posts_summary) if posts_summary else "No representative posts available"
    
    prompt = f"""다음은 클러스터 '{cluster_name}'의 대표 포스트 목록입니다.

대표 포스트:
{posts_text}

이 포스트들을 분석하여 다음을 포함한 간단한 요약을 작성해주세요:
1. 주요 관심사/주제
2. 사용자들의 공통적인 질문이나 니즈
3. 콘텐츠 기획에 활용할 수 있는 인사이트

한국어로 간결하게 작성해주세요 (3-5문장)."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a content strategist analyzing user discussions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
        print(f"Error calling GPT API for representative posts: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in generate_representative_posts_summary: {e}")
        return None

def generate_cluster_summary(cluster_id: str, top_keywords: list, size: int, category: str) -> Optional[str]:
    """클러스터 정보를 기반으로 GPT 요약 생성"""
    client = get_openai_client()
    if not client:
        return None
    
    keywords_text = ", ".join(top_keywords[:20]) if top_keywords else "No keywords"
    
    prompt = f"""다음은 클러스터 '{cluster_id}' ({category})의 정보입니다.

클러스터 정보:
- 크기: {size}개 포스트
- 주요 키워드: {keywords_text}

이 정보를 바탕으로 이 클러스터가 다루는 주제와 주요 관심사를 간단히 요약해주세요.

한국어로 간결하게 작성해주세요 (2-3문장)."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a content analyst summarizing topic clusters."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
        print(f"Error calling GPT API for cluster summary: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in generate_cluster_summary: {e}")
        return None

def generate_master_topics(topic_category: str, reddit_clusters: list, serp_questions: list) -> Optional[str]:
    """마스터 토픽 생성 (GPT 프롬프트 사용)"""
    client = get_openai_client()
    if not client:
        return None
    
    # Reddit 클러스터링 결과 포맷팅
    reddit_data = []
    for cluster in reddit_clusters:
        cluster_info = f"""
- Cluster ID: {cluster.get('cluster_id', 'N/A')}
- Sub Cluster ID: {cluster.get('sub_cluster_id', 'N/A')}
- Cluster Size: {cluster.get('cluster_size', 0)}
- Top Keywords: {', '.join(cluster.get('top_keywords', [])[:10])}
- Summary: {cluster.get('summary', 'N/A')}
"""
        # 대표 포스트 요약 추가
        rep_posts = cluster.get('representative_posts', [])
        if rep_posts:
            cluster_info += "- 대표 포스트:\n"
            for post in rep_posts[:3]:
                title = post.get('title', 'N/A')
                cluster_info += f"  * {title}\n"
        reddit_data.append(cluster_info)
    
    reddit_text = "\n".join(reddit_data) if reddit_data else "Reddit 클러스터링 데이터 없음"
    
    # SERP 질문형 키워드 포맷팅
    serp_text = "\n".join([f"- {q}" for q in serp_questions[:100]]) if serp_questions else "SERP 질문형 키워드 없음"
    
    # GPT 프롬프트 (사용자가 제공한 프롬프트 그대로 사용)
    prompt = f"""너는 데이터 기반 콘텐츠 전략가다.
입력으로 주어진 Reddit 클러스터링 결과와 SERP 질문형 키워드는
"지금 사람들이 실제로 겪는 문제"와
"지금 검색에서 드러나는 정보 수요"를 각각 의미한다.

너의 임무는,
이 두 신호를 결합해
LG전자 블로그/소셜에서 지금 시점에 다뤄야 할
'마스터 토픽(Master Topic)'을 도출하는 것이다.

중요한 기준:
- Reddit 데이터는 "왜 사람들이 이 주제에 관심을 가지는지"
- SERP 질문은 "사람들이 실제로 어떤 질문을 던지고 있는지"
를 보여준다.
둘 중 하나만 사용해서는 안 된다.

각 topic_category에 대해:
- 마스터 토픽 5개만 생성하라.
- 각 마스터 토픽에는 반드시 "Why now"가 포함되어야 한다.
- Why now는 다음 두 요소를 반드시 연결해 설명해야 한다:
  1) Reddit 클러스터에서 관찰된 사용자 맥락/불편/욕구
  2) SERP 질문형 키워드에서 나타난 검색 의도 패턴

출력 시 주의사항:
- "트렌드다", "중요하다" 같은 추상적 표현 금지
- 계절성, 행동 변화, 반복 질문, 문제 전환 같은
  '지금 시점성'을 논리적으로 설명해야 한다.
- 마케팅 문구처럼 쓰지 말고,
  전략 문서에 바로 들어갈 수 있는 톤으로 작성하라.

[입력 데이터]

Topic Category: {topic_category}

[Reddit 클러스터링 결과]
{reddit_text}

[SERP 질문형 키워드]
{serp_text}

[출력 포맷 - 반드시 이 형식 유지]

## {topic_category}

1) **{{마스터 토픽 제목}}**
- **Why now:** {{2~3문장으로, Reddit 신호 + SERP 질문을 연결해 설명}}

2) **{{마스터 토픽 제목}}**
- **Why now:** {{…}}

3) **{{마스터 토픽 제목}}**
- **Why now:** {{…}}

4) **{{마스터 토픽 제목}}**
- **Why now:** {{…}}

5) **{{마스터 토픽 제목}}**
- **Why now:** {{…}}

[검증]
- topic_category는 반드시 {topic_category}만 사용
- 정확히 5개인지 확인
- Why now가 모두 '지금 시점' 관점으로 설명되어 있는지 확인

이 조건을 만족하지 않으면 재생성하라."""

    try:
        print(f"[DEBUG] GPT API 호출 시작: {topic_category}")
        print(f"[DEBUG] Reddit clusters: {len(reddit_clusters)}, SERP questions: {len(serp_questions)}")
        
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
        print(f"[DEBUG] GPT API 호출 성공: {topic_category}, 결과 길이: {len(result)}")
        return result
    except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
        print(f"❌ Error calling GPT API for master topics ({topic_category}): {e}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"❌ Unexpected error in generate_master_topics ({topic_category}): {e}")
        import traceback
        traceback.print_exc()
        return None
