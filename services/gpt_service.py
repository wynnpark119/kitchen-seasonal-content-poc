"""
GPT 분석 서비스

GPT API 호출을 통합 관리하는 서비스 레이어
- 단일 OpenAI 클라이언트 사용
- 에러 처리 및 재시도 로직
- 캐싱 지원 (향후 확장)
"""
import os
import logging
import traceback
from typing import Optional, List, Dict, Any, Tuple
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError, AuthenticationError
import time

from common.openai_client import get_openai_client, is_openai_available

# 로거 설정
logger = logging.getLogger(__name__)


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
    
    def _get_model_name(self) -> str:
        """모델명 가져오기 (환경변수 오버라이드 가능)"""
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    def generate_hs_insight(
        self,
        topic_category: str,
        master_topic_kr: str,
        master_topic_en: str,
        why_now_kr: str,
        why_now_en: str,
        content_angle: str,
        related_topics: List[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        LG전자 HS 콘텐츠 인사이트 생성
        
        Args:
            topic_category: 토픽 카테고리
            master_topic_kr: 마스터 토픽 (한국어)
            master_topic_en: 마스터 토픽 (영어)
            why_now_kr: Why Now (한국어)
            why_now_en: Why Now (영어)
            content_angle: 콘텐츠 앵글
            related_topics: 연관 주제 리스트
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (인사이트 텍스트, 에러 메시지)
            - 성공 시: (인사이트 텍스트, None)
            - 실패 시: (None, 에러 메시지)
        """
        if not is_openai_available():
            error_msg = "OpenAI API 키가 설정되지 않았습니다."
            logger.error(error_msg)
            return None, error_msg
        
        # 연관 주제 포맷팅 (빈 값 처리)
        if related_topics and len(related_topics) > 0:
            related_topics_text = ", ".join([str(t) for t in related_topics[:3] if t])
        else:
            related_topics_text = "None"
        
        # 빈 값 안전 처리
        topic_category = topic_category or "N/A"
        master_topic_kr = master_topic_kr or "N/A"
        master_topic_en = master_topic_en or ""
        why_now_kr = why_now_kr or ""
        why_now_en = why_now_en or ""
        content_angle = content_angle or ""
        
        # 시스템 프롬프트
        system_prompt = """너는 LG전자 HS(생활가전) 관점의 콘텐츠 전략가다.
아래 "마스터 토픽" 정보를 바탕으로, 제품 직접 홍보가 아닌
'봄 시즌 주방 사용 맥락(행동/루틴/문제)을 선점하는 콘텐츠 앵커' 관점에서
실행 가능한 인사이트를 작성해라.

규칙:
- "Reddit" 같은 데이터 출처를 언급하지 말 것
- 제품명/모델명 직접 언급 금지(광고처럼 보이면 실패)
- 기능 나열 금지(생활 시나리오/루틴 중심으로 제안)
- 과장 금지, 실행 가능한 수준으로만 제안
- 아래 출력 포맷을 정확히 준수"""
        
        # 유저 프롬프트
        user_prompt = f"""입력:
[Topic Category] {topic_category}
[Title KR] {master_topic_kr}
[Title EN] {master_topic_en}
[Why Now KR] {why_now_kr}
[Why Now EN] {why_now_en}
[Content Angle] {content_angle}
[Related Topics] {related_topics_text}

출력 포맷(Markdown):
### 📌 LG HS Strategic Content Insight

**A. Consumer Transition Signal**
- (3~5줄)

**B. HS Context / Home Workflow**
- (3~5줄)

**C. Content Activation Plan**
- Blog: (2~3줄)
- Social: (2~3줄)
- Campaign: (2~3줄)

**D. Measurement Ideas**
- (지표 3개, 측정 방식 포함)

**E. Risks & Guardrails**
- (주의/가이드 3개)"""
        
        try:
            # 클라이언트 가져오기 (예외 처리 포함)
            try:
                client = self.client
                logger.debug("OpenAI client initialized successfully")
            except ValueError as e:
                error_msg = str(e)
                logger.exception("OpenAI client initialization error")
                if "OPENAI_API_KEY" in error_msg:
                    error_msg = "API 키를 찾을 수 없습니다. 환경변수 또는 .env 파일을 확인하세요."
                return None, error_msg
            except Exception as e:
                logger.exception("Unexpected error getting OpenAI client")
                return None, f"클라이언트 초기화 오류: {type(e).__name__}: {str(e)}"
            
            # 모델명 가져오기
            model_name = self._get_model_name()
            logger.debug(f"Calling GPT API with model: {model_name}")
            logger.debug(f"Topic: {master_topic_kr[:50]}...")
            
            # 재시도 로직 (최대 2회, 짧은 백오프)
            max_retries = 2
            timeout_seconds = int(os.getenv("OPENAI_TIMEOUT", "60"))
            
            for attempt in range(max_retries + 1):
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000,
                        timeout=timeout_seconds
                    )
                    result = response.choices[0].message.content.strip()
                    logger.info(f"GPT API call successful. Response length: {len(result)}")
                    return result, None
                    
                except AuthenticationError as e:
                    error_msg = f"인증 오류 (401): API 키가 유효하지 않습니다."
                    logger.exception("Authentication error")
                    return None, error_msg
                    
                except RateLimitError as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2  # 2초, 4초 대기
                        logger.warning(f"Rate limit error, retrying after {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = "API 사용량 제한에 도달했습니다. 잠시 후 다시 시도해주세요."
                        logger.exception("Rate limit error (max retries exceeded)")
                        return None, error_msg
                        
                except APITimeoutError as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"Timeout error, retrying after {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"요청 시간 초과 ({timeout_seconds}초). 네트워크 연결을 확인하고 다시 시도해주세요."
                        logger.exception("Timeout error (max retries exceeded)")
                        return None, error_msg
                        
                except APIConnectionError as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"Connection error, retrying after {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = "네트워크 연결 오류가 발생했습니다. 인터넷 연결을 확인해주세요."
                        logger.exception("Connection error (max retries exceeded)")
                        return None, error_msg
                        
                except APIError as e:
                    error_type = type(e).__name__
                    status_code = getattr(e, 'status_code', None)
                    
                    if status_code == 400:
                        error_msg = f"잘못된 요청 (400): 요청 형식이 올바르지 않습니다."
                    elif status_code == 401:
                        error_msg = f"인증 오류 (401): API 키가 유효하지 않습니다."
                    elif status_code == 429:
                        error_msg = f"사용량 제한 (429): API 사용량 제한에 도달했습니다."
                    else:
                        error_msg = f"API 오류 ({status_code or error_type}): {str(e)}"
                    
                    logger.exception(f"API error ({error_type}, status={status_code})")
                    return None, error_msg
                    
            # 모든 재시도 실패
            error_msg = "모든 재시도가 실패했습니다."
            logger.error(error_msg)
            return None, error_msg
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"예상치 못한 오류 ({error_type}): {str(e)}"
            logger.exception("Unexpected error in generate_hs_insight")
            return None, error_msg


# 싱글톤 인스턴스
_gpt_service: Optional[GPTService] = None


def get_gpt_service() -> GPTService:
    """GPT 서비스 싱글톤 인스턴스 반환"""
    global _gpt_service
    
    # 클래스 레벨에서 메서드 존재 확인
    if not hasattr(GPTService, 'generate_hs_insight'):
        import logging
        logger = logging.getLogger(__name__)
        logger.error("GPTService class missing generate_hs_insight method! This indicates a code loading issue.")
        raise AttributeError(
            "GPTService class does not have generate_hs_insight method. "
            "This usually means Streamlit is using a cached version of the module. "
            "Please restart Streamlit completely (stop and restart)."
        )
    
    # 인스턴스 레벨에서 메서드 존재 확인 및 강제 리셋
    if _gpt_service is not None:
        if not hasattr(_gpt_service, 'generate_hs_insight'):
            # 이전 버전의 인스턴스가 캐시되어 있음 - 강제 리셋
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("GPT service instance missing generate_hs_insight method, resetting instance...")
            _gpt_service = None
    
    if _gpt_service is None:
        _gpt_service = GPTService()
        # 생성 후 메서드 존재 확인
        if not hasattr(_gpt_service, 'generate_hs_insight'):
            import logging
            logger = logging.getLogger(__name__)
            logger.error("New GPT service instance also missing generate_hs_insight method!")
            raise AttributeError(
                "GPTService instance does not have generate_hs_insight method. "
                "Please restart Streamlit completely (Ctrl+C to stop, then restart)."
            )
    
    return _gpt_service


def reset_gpt_service():
    """GPT 서비스 싱글톤 인스턴스 리셋 (테스트/디버깅용)"""
    global _gpt_service
    _gpt_service = None
