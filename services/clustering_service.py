"""
클러스터링 데이터 서비스

클러스터링 결과 조회 및 처리 로직
JSON 파일을 직접 로드하여 사용
"""
from typing import List, Dict, Any, Union, Optional
import pandas as pd
import numpy as np
import json
from pathlib import Path

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
    
    def __init__(self):
        """JSON 파일 경로 설정"""
        project_root = Path(__file__).parent.parent
        self.json_path = project_root / "clustering_results.json"
        self._json_data: Optional[Dict[str, Any]] = None
    
    def _load_json(self) -> Optional[Dict[str, Any]]:
        """JSON 파일 로드 (캐싱)"""
        if self._json_data is not None:
            return self._json_data
        
        if not self.json_path.exists():
            print(f"⚠️ clustering_results.json 파일을 찾을 수 없습니다: {self.json_path}")
            return None
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self._json_data = json.load(f)
            return self._json_data
        except Exception as e:
            print(f"❌ JSON 파일 로드 실패: {e}")
            return None
    
    def get_all_clusters(self) -> pd.DataFrame:
        """전체 클러스터링 결과 조회 (JSON 파일에서)"""
        try:
            json_data = self._load_json()
            if json_data is None:
                # Fallback: DB에서 조회
                print("⚠️ JSON 파일이 없어 DB에서 조회합니다.")
                return get_clustering_results_from_db()
            
            clusters = json_data.get('clusters', [])
            if not clusters:
                return pd.DataFrame()
            
            # JSON 데이터를 DataFrame으로 변환
            rows = []
            for cluster in clusters:
                row = {
                    'cluster_id': cluster.get('cluster_id', ''),
                    'cluster_name': cluster.get('cluster_id', ''),  # cluster_id를 cluster_name으로도 사용
                    'topic_category': cluster.get('topic_category'),
                    'sub_cluster_index': cluster.get('sub_cluster_index'),
                    'size': cluster.get('size', 0),
                    'post_ids': cluster.get('post_ids', []),
                    'representative_post_ids': cluster.get('representative_post_ids', []),
                    'representative_count': len(cluster.get('representative_post_ids', [])),
                    'top_keywords': cluster.get('top_keywords', []),
                    'summary': cluster.get('summary', ''),
                    'posts': cluster.get('posts', [])  # 전체 포스트 정보 포함
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            print(f"✅ JSON 파일에서 {len(df)}개 클러스터 로드 완료")
            return df
            
        except Exception as e:
            print(f"Error loading clustering results from JSON: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: DB에서 조회
            try:
                return get_clustering_results_from_db()
            except:
                return pd.DataFrame()
    
    def get_clusters_by_category(self, topic_category: str) -> pd.DataFrame:
        """특정 카테고리의 클러스터 조회"""
        df = self.get_all_clusters()
        if len(df) == 0:
            return df
        return df[df['topic_category'] == topic_category].copy()
    
    def get_category_overview(self) -> pd.DataFrame:
        """카테고리별 통계 오버뷰 조회 (JSON 파일만 사용)"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # JSON 파일에서만 조회 (DB fallback 제거)
            json_data = self._load_json()
            if json_data is None:
                logger.warning(f"clustering_results.json 파일을 찾을 수 없습니다: {self.json_path}")
                print(f"⚠️ clustering_results.json 파일을 찾을 수 없습니다: {self.json_path}")
                return pd.DataFrame()
            
            from collections import defaultdict
            category_stats = defaultdict(lambda: {'posts': 0, 'comments': 0, 'clusters': 0})
            
            # 각 클러스터의 통계 집계
            clusters = json_data.get('clusters', [])
            logger.info(f"Processing {len(clusters)} clusters from JSON file")
            
            for cluster in clusters:
                category = cluster.get('topic_category', 'UNKNOWN')
                if not category or category == 'UNKNOWN':
                    continue
                    
                category_stats[category]['clusters'] += 1
                cluster_size = cluster.get('size', 0)
                category_stats[category]['posts'] += cluster_size
                
                # 각 포스트의 코멘트 수 합산
                posts = cluster.get('posts', [])
                for post in posts:
                    num_comments = post.get('num_comments', 0)
                    if num_comments:
                        category_stats[category]['comments'] += int(num_comments)
            
            # DataFrame으로 변환
            rows = []
            for category, stats in sorted(category_stats.items()):
                rows.append({
                    'category': category,
                    'clusters': stats['clusters'],
                    'posts': stats['posts'],
                    'comments': stats['comments']
                })
            
            if rows:
                df = pd.DataFrame(rows)
                logger.info(f"✅ JSON에서 카테고리별 통계 로드 완료: {len(df)}개 카테고리")
                print(f"✅ JSON에서 카테고리별 통계 로드 완료: {len(df)}개 카테고리")
                # 각 카테고리별 상세 로그
                for _, row in df.iterrows():
                    print(f"  - {row['category']}: 클러스터 {row['clusters']}개, 포스트 {row['posts']}개, 코멘트 {row['comments']:,}개")
                return df
            else:
                logger.warning("카테고리별 집계 결과가 없습니다.")
                print("⚠️ 카테고리별 집계 결과가 없습니다.")
                return pd.DataFrame()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error getting category overview")
            print(f"Error getting category overview: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_reddit_clusters_for_master_topic(self, topic_category: str) -> List[Dict[str, Any]]:
        """마스터 토픽 생성을 위한 Reddit 클러스터 조회"""
        try:
            return get_reddit_clustering_for_master_topic(topic_category)
        except Exception as e:
            print(f"Error loading reddit clusters for {topic_category}: {e}")
            return []
    
    def get_representative_posts(self, cluster_id: Union[int, str, np.integer, np.int64], limit: int = 5) -> pd.DataFrame:
        """
        클러스터의 대표 포스트 조회 (JSON 파일에서)
        
        Args:
            cluster_id: 클러스터 ID (문자열 또는 숫자)
            limit: 조회할 포스트 수
            
        Returns:
            대표 포스트 DataFrame
        """
        try:
            json_data = self._load_json()
            if json_data is None:
                # Fallback: DB에서 조회
                cluster_id_int = to_python_int(cluster_id) if isinstance(cluster_id, (int, np.integer, np.int64)) else int(str(cluster_id).split('_')[-1])
                return get_cluster_representative_posts(cluster_id_int, limit=limit)
            
            # cluster_id를 문자열로 변환 (JSON의 cluster_id는 문자열 형식: "SPRING_RECIPES_1")
            cluster_id_str = str(cluster_id)
            
            # JSON에서 해당 클러스터 찾기
            clusters = json_data.get('clusters', [])
            cluster = None
            for c in clusters:
                if str(c.get('cluster_id', '')) == cluster_id_str:
                    cluster = c
                    break
            
            if cluster is None:
                print(f"⚠️ 클러스터를 찾을 수 없습니다: {cluster_id_str}")
                return pd.DataFrame()
            
            # 대표 포스트 ID 목록 가져오기
            representative_post_ids = cluster.get('representative_post_ids', [])[:limit]
            posts = cluster.get('posts', [])
            
            # posts 배열에서 대표 포스트만 필터링
            representative_posts = [
                post for post in posts 
                if post.get('post_id') in representative_post_ids
            ]
            
            if not representative_posts:
                # posts 배열이 없거나 매칭되지 않으면 빈 DataFrame 반환
                return pd.DataFrame()
            
            # DataFrame으로 변환
            df = pd.DataFrame(representative_posts)
            print(f"✅ 클러스터 {cluster_id_str}의 대표 포스트 {len(df)}개 로드 완료")
            return df
            
        except Exception as e:
            print(f"Error loading representative posts for cluster {cluster_id}: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: DB에서 조회
            try:
                cluster_id_int = to_python_int(cluster_id) if isinstance(cluster_id, (int, np.integer, np.int64)) else int(str(cluster_id).split('_')[-1])
                return get_cluster_representative_posts(cluster_id_int, limit=limit)
            except:
                return pd.DataFrame()


# 싱글톤 인스턴스
_clustering_service: Optional[ClusteringService] = None


def get_clustering_service(force_reload: bool = False) -> ClusteringService:
    """
    클러스터링 서비스 싱글톤 인스턴스 반환
    
    Args:
        force_reload: True면 기존 인스턴스를 무시하고 새로 생성
    """
    global _clustering_service
    if _clustering_service is None or force_reload:
        _clustering_service = ClusteringService()
    return _clustering_service
