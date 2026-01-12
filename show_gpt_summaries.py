#!/usr/bin/env python3
"""클러스터링 결과의 GPT 요약만 출력"""
import sys
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
    import os
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

from web.db_queries import get_clustering_results_from_db
from web.gpt_utils import generate_cluster_summary

print("=" * 80)
print("클러스터링 결과 GPT 요약")
print("=" * 80)
print()

try:
    # DB에서 클러스터링 결과 조회
    clusters_df = get_clustering_results_from_db()
    
    if len(clusters_df) == 0:
        print("⚠️ 클러스터 데이터가 없습니다.")
        sys.exit(1)
    
    print(f"총 {len(clusters_df)}개 클러스터\n")
    print("=" * 80)
    print()
    
    # 각 클러스터에 대해 GPT 요약 생성
    for idx, (_, cluster_row) in enumerate(clusters_df.iterrows(), 1):
        cluster_id = cluster_row['cluster_id']
        cluster_id_str = str(cluster_id)
        cluster_name = cluster_row.get('cluster_name', f"Cluster_{cluster_id}")
        topic_category = cluster_row.get('topic_category', 'Unknown')
        size = cluster_row.get('size', 0)
        
        # top_keywords 가져오기
        top_keywords = cluster_row.get('top_keywords', [])
        if not isinstance(top_keywords, list):
            top_keywords = []
        
        print(f"[{idx}] {cluster_name} ({topic_category})")
        print(f"     Size: {size}, Keywords: {len(top_keywords)}개")
        print()
        
        # GPT 요약 생성
        print("     📝 GPT 요약:")
        gpt_summary = generate_cluster_summary(
            cluster_id_str,
            top_keywords[:10] if top_keywords else [],
            int(size),
            topic_category
        )
        
        if gpt_summary:
            # 요약을 들여쓰기해서 출력
            for line in gpt_summary.split('\n'):
                print(f"     {line}")
        else:
            print("     ⚠️ GPT API 호출 실패")
        
        print()
        print("-" * 80)
        print()
    
    print("=" * 80)
    print("완료!")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
