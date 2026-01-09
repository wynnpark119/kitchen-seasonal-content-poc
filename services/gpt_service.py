"""
GPT 분석 서비스

GPT API 호출을 통합 관리하는 서비스 레이어
- 단일 OpenAI 클라이언트 사용
- 에러 처리 및 재시도 로직
- 캐싱 지원 (향후 확장)
"""
from typing import Optional, List, Dict, Any
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError
import time

from common.openai_client import get_openai_client, is_openai_available


class GPTService:
    """GPT 분석 서비스 클래스"""
    
    def __init__(self):
        """서비스 초기화"""
        self._client = None
    
    @property
    def client(self):
        """OpenAI 클라이언트 (지연 로딩)"""
        if self._client is None:
            self._client = get_openai_client()
        return self._client
    
    def generate_cluster_summary(
        self, 
        cluster_id: str, 
        top_keywords: List[str], 
        size: int, 
        category: str
    ) -> Optional[str]:
        """
        클러스터 요약 생성
        
        Args:
            cluster_id: 클러스터 ID
            top_keywords: 상위 키워드 리스트
            size: 클러스터 크기
            category: 카테고리
            
        Returns:
            요약 텍스트 또는 None (실패 시)
        """
        if not is_openai_available():
            return None
        
        keywords_text = ", ".join(top_keywords[:20]) if top_keywords else "No keywords"
        
        prompt = f"""다음은 클러스터 '{cluster_id}' ({category})의 정보입니다.

클러스터 정보:
- 크기: {size}개 포스트
- 주요 키워드: {keywords_text}

이 정보를 바탕으로 이 클러스터가 다루는 주제와 주요 관심사를 간단히 요약해주세요.

한국어로 간결하게 작성해주세요 (2-3문장)."""

        try:
            response = self.client.chat.completions.create(
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
    
    def generate_master_topics(
        self,
        topic_category: str,
        reddit_clusters: List[Dict[str, Any]],
        serp_questions: List[str]
    ) -> Optional[str]:
        """
        마스터 토픽 생성
        
        Args:
            topic_category: 토픽 카테고리
            reddit_clusters: Reddit 클러스터링 결과 리스트
            serp_questions: SERP 질문형 키워드 리스트
            
        Returns:
            마스터 토픽 마크다운 텍스트 또는 None (실패 시)
        """
        if not is_openai_available():
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
        
        # GPT 프롬프트
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
            # 재시도 로직 (최대 1회)
            max_retries = 1
            for attempt in range(max_retries + 1):
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a data-driven content strategist specializing in creating master topics for LG Electronics blog and social media content."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000
                    )
                    return response.choices[0].message.content.strip()
                except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2  # 2초, 4초 대기
                        print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise
                        
        except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
            print(f"Error calling GPT API for master topics ({topic_category}): {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in generate_master_topics ({topic_category}): {e}")
            return None


# 싱글톤 인스턴스
_gpt_service: Optional[GPTService] = None


def get_gpt_service() -> GPTService:
    """GPT 서비스 싱글톤 인스턴스 반환"""
    global _gpt_service
    if _gpt_service is None:
        _gpt_service = GPTService()
    return _gpt_service
