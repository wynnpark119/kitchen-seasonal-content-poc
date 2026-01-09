"""
클러스터링 데이터 서비스

클러스터링 결과 조회 및 처리 로직
"""
from typing import List, Dict, Any, Union
import pandas as pd
import numpy as np

from web.db_queries import (
    get_clustering_results_from_db,
    get_cluster_representative_posts,
    get_reddit_clustering_for_master_topic
)


def to_python_int(value: Union[int, np.integer, np.int64]) -> int:
    """
    numpy 타입을 Python int로 변환
    
    Args:
        value: 변환할 값
        
    Returns:
        Python int
    """
    if isinstance(value, (np.integer, np.int64)):
        return int(value)
    return int(value) if isinstance(value, (int, float)) else value


class ClusteringService:
    """클러스터링 데이터 서비스"""
    
    def get_all_clusters(self) -> pd.DataFrame:
        """전체 클러스터링 결과 조회"""
        try:
            return get_clustering_results_from_db()
        except Exception as e:
            print(f"Error loading clustering results: {e}")
            return pd.DataFrame()
    
    def get_clusters_by_category(self, topic_category: str) -> pd.DataFrame:
        """특정 카테고리의 클러스터 조회"""
        df = self.get_all_clusters()
        if len(df) == 0:
            return df
        return df[df['topic_category'] == topic_category].copy()
    
    def get_reddit_clusters_for_master_topic(self, topic_category: str) -> List[Dict[str, Any]]:
        """마스터 토픽 생성을 위한 Reddit 클러스터 조회"""
        try:
            return get_reddit_clustering_for_master_topic(topic_category)
        except Exception as e:
            print(f"Error loading reddit clusters for {topic_category}: {e}")
            return []
    
    def get_representative_posts(self, cluster_id: Union[int, np.integer, np.int64], limit: int = 5) -> pd.DataFrame:
        """
        클러스터의 대표 포스트 조회
        
        Args:
            cluster_id: 클러스터 ID (numpy 타입 포함)
            limit: 조회할 포스트 수
            
        Returns:
            대표 포스트 DataFrame
        """
        try:
            # numpy 타입을 Python int로 변환
            cluster_id_int = to_python_int(cluster_id)
            return get_cluster_representative_posts(cluster_id_int, limit=limit)
        except Exception as e:
            print(f"Error loading representative posts for cluster {cluster_id}: {e}")
            return pd.DataFrame()


# 싱글톤 인스턴스
_clustering_service: ClusteringService = None


def get_clustering_service() -> ClusteringService:
    """클러스터링 서비스 싱글톤 인스턴스 반환"""
    global _clustering_service
    if _clustering_service is None:
        _clustering_service = ClusteringService()
    return _clustering_service
