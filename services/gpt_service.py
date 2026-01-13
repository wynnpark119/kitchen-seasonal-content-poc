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
        related_topics: List[str],
        prompt_version: str = "planning_v2"
    ) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, str]]]:
        """
        AI 콘텐츠 플래닝 생성
        
        콘텐츠 기획자가 바로 실행 방향을 잡을 수 있도록
        '블로그는 어떻게 쓰고, 소셜은 어떻게 쓰는지'를 명확하게 제시하는 콘텐츠 플래닝을 생성합니다.
        
        Args:
            topic_category: 토픽 카테고리
            master_topic_kr: 마스터 토픽 (한국어)
            master_topic_en: 마스터 토픽 (영어)
            why_now_kr: Why Now (한국어) - 사용하지 않음
            why_now_en: Why Now (영어) - 사용하지 않음
            content_angle: 콘텐츠 앵글
            related_topics: 연관 주제 리스트
            prompt_version: 프롬프트 버전 (캐시 무효화용)
            
        Returns:
            Tuple[Optional[str], Optional[str], Optional[Dict]]: (콘텐츠 플래닝 텍스트, 에러 메시지, 디버그 정보)
            - 성공 시: (콘텐츠 플래닝 텍스트, None, 디버그 정보)
            - 실패 시: (None, 에러 메시지, 디버그 정보)
        """
        if not is_openai_available():
            error_msg = "OpenAI API 키가 설정되지 않았습니다."
            logger.error(error_msg)
            return None, error_msg, None
        
        # 디버그 정보 초기화
        debug_info = {
            "function_name": "generate_hs_insight",
            "prompt_version": prompt_version,
            "model": None,
            "temperature": 0.2,
            "user_prompt": None,
            "response_preview": None
        }
        
        # 연관 주제 포맷팅 (빈 값 처리)
        if related_topics and len(related_topics) > 0:
            related_topics_text = ", ".join([str(t) for t in related_topics[:3] if t])
        else:
            related_topics_text = "없음"
        
        # 빈 값 안전 처리 (why_now는 사용하지 않음)
        topic_category = topic_category or "N/A"
        master_topic_kr = master_topic_kr or "N/A"
        master_topic_en = master_topic_en or ""
        content_angle = content_angle or ""
        
        # 시스템 프롬프트 (완전히 새로 작성)
        system_prompt = """당신은 글로벌 가전 브랜드(주방가전)에서 블로그·소셜·캠페인 콘텐츠를 실제로 설계하는 시니어 콘텐츠 플래너입니다.
전략 설명이 아니라 실행 가능한 콘텐츠 기획안을 제시해야 합니다.

🚫 절대 사용 금지 (위반 시 즉시 실패):
- "📌 LG HS Strategic Content Insight" 타이틀 절대 사용 금지
- "A.", "B.", "C.", "D.", "E." 같은 알파벳 섹션 절대 사용 금지
- "Customer Transition Signal", "HS Context" 같은 이전 섹션명 절대 사용 금지
- 추상적 인사이트, 이론 설명 금지 ("왜 중요하다", "전환 시점이다" 같은 문장 최소화)
- 이미 화면에 표시된 '선정 이유(Why)'를 재설명하지 않음
- "조회수", "참여율", "KPI", "지표" 같은 성과 측정 관련 단어 전부 금지
- "인사이트", "전환", "니즈" 같은 마케팅 용어 남용 금지
- Reddit, Google, 검색 데이터 언급 금지

✅ 반드시 사용해야 하는 형식 (정확히 이 형식만 사용):
- 타이틀: "### 콘텐츠 활용 인사이트" (반드시 이 정확한 텍스트 사용)
- 섹션 1: "#### 1. 글로벌 블로그 콘텐츠 기획 방향 (How-to 중심)"
- 섹션 2: "#### 2. 소셜 콘텐츠 기획 방향 (Instagram 중심)"
- 섹션 3: "#### 3. 시리즈 / 캠페인 확장 아이디어"
- 섹션 4: "#### 4. LG전자 HS 관점에서의 콘텐츠 역할"

✅ 필수 원칙:
- 콘텐츠 기획자 관점에서의 설계 언어 사용
- 콘텐츠 구조, 컷 구성, 메시지 밀도, 독자 행동 기준 명확히 제시
- "읽고 나면 / 보고 나면 무엇을 하게 되는가"가 항상 드러나야 함
- 문장은 기획안 문서에 바로 복사 가능한 수준으로 작성
- 한국어 출력 (공식/기획자용 톤)
- 모든 채널에 공통 적용 가능한 프레임 (특정 제품/기능 설명 ❌, 주방 사용 맥락과 루틴 중심)"""
        
        # 유저 프롬프트 (완전히 새로 작성)
        user_prompt = f"""⚠️ 매우 중요: 반드시 아래 형식만 사용하라. 다른 형식 사용 절대 금지.

[입력 데이터]
- 선택된 마스터 토픽: {master_topic_kr}
- 토픽 카테고리: {topic_category}
- 콘텐츠 앵글: {content_angle}
- 연관 주제: {related_topics_text}

⚠️ 주의: 이미 도출된 선정 이유(Why this topic exists)는 재설명하지 말 것.

📤 출력 포맷 (반드시 이 구조 유지):

### 콘텐츠 활용 인사이트

#### 1. 글로벌 블로그 콘텐츠 기획 방향 (How-to 중심)

• 콘텐츠 목적
독자가 글을 끝까지 읽었을 때 오늘 저녁 바로 실행할 수 있어야 함

• 권장 콘텐츠 구조
- Why: 이 주제의 요리가 평일에 특히 유효한 이유 (1~2문장)
- What: 이 방식이 기존 요리보다 나은 핵심 포인트 3가지
- How: 실제 조리 흐름을 기준으로 한 단계 구성 (재료 → 조리 → 마무리 → 보관까지 이어지는 구조)
- Practical Tips: 실패하기 쉬운 포인트, 남은 재료/다음 끼니로 연결되는 팁
- 편집 가이드: 이미지/도식이 필요한 지점 명시, 스크롤 중단 없이 읽히는 문단 길이 기준 제안

[위 구조에 맞춰 이 마스터 토픽("{master_topic_kr}")에 대한 구체적인 블로그 콘텐츠 기획안을 작성하라. 기획안 문서에 바로 복사 가능한 수준으로 작성하라.]

#### 2. 소셜 콘텐츠 기획 방향 (Instagram 중심)

• 핵심 목표
설명을 읽지 않아도 한 번에 이해되는 콘텐츠

• 추천 메시지 유형
- 바로 써먹을 수 있는 문장형 훅 제안 (3~5개)
- 판단을 대신 내려주는 단정형 문구 사용

• 비주얼 구성 가이드
- 한 컷 완결 / Before–After / 조리 중간 컷 중 무엇이 적합한지 명시
- 촬영 각도·구도에 대한 구체적 제안

• 운영 관점 팁
- 반복 노출해도 피로하지 않은 포맷
- 시리즈화 시 유지해야 할 포맷 규칙

[위 구조에 맞춰 이 마스터 토픽("{master_topic_kr}")에 대한 구체적인 소셜 콘텐츠 기획안을 작성하라. 기획안 문서에 바로 복사 가능한 수준으로 작성하라.]

#### 3. 시리즈 / 캠페인 확장 아이디어

• 캠페인의 성격 정의
'도전'이 아닌 '루틴 제안'으로 보이게 설계

• 시리즈 구성 예시
- 기간 (예: 5일 / 1주 / 평일 기준)
- 하루 단위 콘텐츠의 역할 분담

• 확장 가능성
다른 주제(정리, 보관, 스타일링)와 연결될 수 있는 지점 제시

[위 구조에 맞춰 이 마스터 토픽("{master_topic_kr}")에 대한 구체적인 시리즈/캠페인 확장 아이디어를 작성하라. 기획안 문서에 바로 복사 가능한 수준으로 작성하라.]

#### 4. LG전자 HS 관점에서의 콘텐츠 역할

• 브랜드 노출 방식
제품 설명 없이도 '이 브랜드는 주방 사용 흐름을 이해하고 있다'는 인식이 생기도록 설계

• 브랜드가 담당해야 할 역할
- 고객의 선택 피로를 줄이는 기준 제시자
- 복잡한 주방 행동을 정리해 주는 가이드

• 주의할 점
과도한 기능 강조, 다이어트·효율 강박으로 오해될 수 있는 메시지 회피

[위 구조에 맞춰 이 마스터 토픽("{master_topic_kr}")에서 LG전자 HS가 가져야 할 구체적인 콘텐츠 역할을 작성하라. 기획안 문서에 바로 복사 가능한 수준으로 작성하라.]

[최종 검증 - 반드시 확인 후 출력]
1. 타이틀이 정확히 "### 콘텐츠 활용 인사이트"인지 확인
2. 섹션이 정확히 "#### 1. 글로벌 블로그 콘텐츠 기획 방향 (How-to 중심)", "#### 2. 소셜 콘텐츠 기획 방향 (Instagram 중심)", "#### 3. 시리즈 / 캠페인 확장 아이디어", "#### 4. LG전자 HS 관점에서의 콘텐츠 역할"인지 확인
3. "A.", "B.", "C.", "D.", "E." 같은 알파벳 섹션이 전혀 없는지 확인
4. 추상적 인사이트, 이론 설명이 없는지 확인 ("왜 중요하다", "전환 시점이다" 같은 문장 최소화)
5. 선정 이유(Why)를 재설명하지 않았는지 확인
6. "인사이트", "전환", "니즈" 같은 마케팅 용어를 남용하지 않았는지 확인
7. 문장이 기획안 문서에 바로 복사 가능한 수준인지 확인
8. "읽고 나면 / 보고 나면 무엇을 하게 되는가"가 드러나는지 확인
9. 특정 제품/기능 설명이 아닌 주방 사용 맥락과 루틴 중심인지 확인
10. 콘텐츠 구조, 컷 구성, 메시지 밀도가 명확히 제시되었는지 확인

위 모든 항목을 확인한 후에만 출력하라. 하나라도 위반되면 다시 작성하라."""
        
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
                return None, error_msg, debug_info
            except Exception as e:
                logger.exception("Unexpected error getting OpenAI client")
                error_msg = f"클라이언트 초기화 오류: {type(e).__name__}: {str(e)}"
                return None, error_msg, debug_info
            
            # 모델명 가져오기
            model_name = self._get_model_name()
            debug_info["model"] = model_name
            logger.debug(f"Calling GPT API with model: {model_name}, prompt_version: {prompt_version}")
            logger.debug(f"Topic: {master_topic_kr[:50]}...")
            
            # 디버그 정보에 프롬프트 저장
            debug_info["user_prompt"] = user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt
            
            # 재시도 로직 (최대 3회, 짧은 백오프)
            max_retries = 3
            timeout_seconds = int(os.getenv("OPENAI_TIMEOUT", "60"))
            
            for attempt in range(max_retries + 1):
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2,  # 더 낮춰서 일관된 형식 유지
                        max_tokens=2500,  # 충분한 길이 보장
                        timeout=timeout_seconds
                    )
                    result = response.choices[0].message.content.strip()
                    logger.info(f"GPT API call successful. Response length: {len(result)}")
                    
                    # 디버그 정보에 응답 저장
                    debug_info["response_preview"] = result[:500] + "..." if len(result) > 500 else result
                    
                    # 응답 검증: 이전 형식이 포함되어 있으면 에러
                    forbidden_patterns = [
                        "LG HS Strategic Content Insight",
                        "A. Customer Transition Signal",
                        "B. HS Context",
                        "C. Content Activation Direction",
                        "D. Brand Role",
                        "E. Risks & Guardrails",
                        "Customer Transition Signal",
                        "HS Context / Home Workflow"
                    ]
                    
                    for pattern in forbidden_patterns:
                        if pattern in result:
                            logger.error(f"Forbidden pattern '{pattern}' found in response. Attempt {attempt + 1}/{max_retries + 1}")
                            # 재시도
                            if attempt < max_retries:
                                wait_time = (attempt + 1) * 2
                                logger.warning(f"Retrying after {wait_time}s due to forbidden pattern")
                                time.sleep(wait_time)
                                break
                            else:
                                error_msg = f"응답에 금지된 형식이 포함되어 있습니다: {pattern}. 프롬프트 버전: {prompt_version}"
                                debug_info["error"] = error_msg
                                return None, error_msg, debug_info
                    else:
                        # for 루프가 break 없이 완료되면 (금지 패턴 없음)
                        # 올바른 형식 확인
                        if "### 콘텐츠 활용 인사이트" not in result:
                            logger.warning(f"올바른 타이틀이 없습니다. Attempt {attempt + 1}/{max_retries + 1}")
                            if attempt < max_retries:
                                wait_time = (attempt + 1) * 2
                                time.sleep(wait_time)
                                continue
                            else:
                                error_msg = f"올바른 타이틀이 없습니다. 프롬프트 버전: {prompt_version}"
                                debug_info["error"] = error_msg
                                return None, error_msg, debug_info
                        
                        # 모든 검증 통과
                        return result, None, debug_info
                    
                except AuthenticationError as e:
                    error_msg = f"인증 오류 (401): API 키가 유효하지 않습니다."
                    logger.exception("Authentication error")
                    debug_info["error"] = error_msg
                    return None, error_msg, debug_info
                    
                except RateLimitError as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2  # 2초, 4초 대기
                        logger.warning(f"Rate limit error, retrying after {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = "API 사용량 제한에 도달했습니다. 잠시 후 다시 시도해주세요."
                        logger.exception("Rate limit error (max retries exceeded)")
                        debug_info["error"] = error_msg
                        return None, error_msg, debug_info
                        
                except APITimeoutError as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"Timeout error, retrying after {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"요청 시간 초과 ({timeout_seconds}초). 네트워크 연결을 확인하고 다시 시도해주세요."
                        logger.exception("Timeout error (max retries exceeded)")
                        debug_info["error"] = error_msg
                        return None, error_msg, debug_info
                        
                except APIConnectionError as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"Connection error, retrying after {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = "네트워크 연결 오류가 발생했습니다. 인터넷 연결을 확인해주세요."
                        logger.exception("Connection error (max retries exceeded)")
                        debug_info["error"] = error_msg
                        return None, error_msg, debug_info
                        
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
                    debug_info["error"] = error_msg
                    return None, error_msg, debug_info
                    
            # 모든 재시도 실패
            error_msg = "모든 재시도가 실패했습니다."
            logger.error(error_msg)
            debug_info["error"] = error_msg
            return None, error_msg, debug_info
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"예상치 못한 오류 ({error_type}): {str(e)}"
            logger.exception("Unexpected error in generate_hs_insight")
            debug_info["error"] = error_msg
            return None, error_msg, debug_info
    
    def classify_query_content_type(
        self,
        query: str,
        aio_text: Optional[str] = None
    ) -> Optional[str]:
        """
        쿼리를 evergreen/seasonal/other로 분류
        
        Args:
            query: 검색 쿼리
            aio_text: AI Overview 텍스트 (선택적)
            
        Returns:
            'evergreen', 'seasonal', 'other' 중 하나 또는 None (실패 시)
        """
        if not is_openai_available():
            return None
        
        # 프롬프트 구성
        context = f"Query: {query}"
        if aio_text:
            context += f"\n\nAI Overview: {aio_text[:500]}"
        
        prompt = f"""다음 검색 쿼리를 분석하여 콘텐츠 타입을 분류해주세요.

{context}

분류 기준:
- **evergreen**: 계절과 무관하게 지속적으로 검색되는 주제 (예: 냉장고 정리, 채소 보관법, 요리 기본기)
- **seasonal**: 특정 계절(특히 봄)에 집중적으로 검색되는 주제 (예: 봄 레시피, 봄 주방 인테리어, 봄 식재료)
- **other**: 위 두 가지에 명확히 속하지 않는 주제

반드시 다음 중 하나만 반환하세요: evergreen, seasonal, other
추가 설명 없이 단어만 반환하세요."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a content classification assistant. Return only one word: evergreen, seasonal, or other."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=10
            )
            result = response.choices[0].message.content.strip().lower()
            
            # 결과 검증
            if result in ['evergreen', 'seasonal', 'other']:
                return result
            else:
                logger.warning(f"Unexpected classification result: {result}, defaulting to 'other'")
                return 'other'
                
        except Exception as e:
            logger.error(f"Error classifying query content type: {e}")
            return None


# 싱글톤 인스턴스
_gpt_service: Optional[GPTService] = None


def get_gpt_service() -> GPTService:
    """GPT 서비스 싱글톤 인스턴스 반환"""
    global _gpt_service
    
    # 필수 메서드 목록
    required_methods = ['generate_hs_insight', 'classify_query_content_type']
    
    # 클래스 레벨에서 메서드 존재 확인
    for method_name in required_methods:
        if not hasattr(GPTService, method_name):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"GPTService class missing {method_name} method! This indicates a code loading issue.")
            raise AttributeError(
                f"GPTService class does not have {method_name} method. "
                "This usually means Streamlit is using a cached version of the module. "
                "Please restart Streamlit completely (stop and restart)."
            )
    
    # 인스턴스 레벨에서 메서드 존재 확인 및 강제 리셋
    if _gpt_service is not None:
        for method_name in required_methods:
            if not hasattr(_gpt_service, method_name):
                # 이전 버전의 인스턴스가 캐시되어 있음 - 강제 리셋
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"GPT service instance missing {method_name} method, resetting instance...")
                _gpt_service = None
                break
    
    if _gpt_service is None:
        _gpt_service = GPTService()
        # 생성 후 메서드 존재 확인
        for method_name in required_methods:
            if not hasattr(_gpt_service, method_name):
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"New GPT service instance also missing {method_name} method!")
                raise AttributeError(
                    f"GPTService instance does not have {method_name} method. "
                    "Please restart Streamlit completely (Ctrl+C to stop, then restart)."
                )
    
    return _gpt_service


def reset_gpt_service():
    """GPT 서비스 싱글톤 인스턴스 리셋 (테스트/디버깅용)"""
    global _gpt_service
    _gpt_service = None
