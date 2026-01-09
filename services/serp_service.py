"""
SERP 데이터 서비스

SERP 질문형 키워드 조회 및 처리 로직
"""
from typing import List

from web.db_queries import (
    get_serp_aio,
    get_serp_questions_for_master_topic
)


class SERPService:
    """SERP 데이터 서비스"""
    
    def get_all_serp_data(self):
        """전체 SERP 데이터 조회"""
        try:
            return get_serp_aio()
        except Exception as e:
            print(f"Error loading SERP data: {e}")
            return None
    
    def get_questions_for_master_topic(self, topic_category: str) -> List[str]:
        """마스터 토픽 생성을 위한 SERP 질문형 키워드 조회"""
        try:
            return get_serp_questions_for_master_topic(topic_category)
        except Exception as e:
            print(f"Error loading SERP questions for {topic_category}: {e}")
            return []


# 싱글톤 인스턴스
_serp_service: SERPService = None


def get_serp_service() -> SERPService:
    """SERP 서비스 싱글톤 인스턴스 반환"""
    global _serp_service
    if _serp_service is None:
        _serp_service = SERPService()
    return _serp_service
