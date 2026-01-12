#!/usr/bin/env python3
"""
로컬에서 클러스터링을 실행하고 JSON으로 저장하는 스크립트

DB 연결 없이 로컬에서만 실행하여 클러스터링 결과를 JSON 파일로 저장합니다.
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter, defaultdict
import re

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.config import CATEGORIES
from worker.pipeline.tfidf_clustering import (
    assign_post_to_category, 
    extract_text_from_post,
    extract_top_keywords,
    generate_cluster_summary,
    cluster_posts_within_category
)
from worker.pipeline.preprocess import clean_text, is_deleted_post

def load_reddit_json(json_path: str) -> List[Dict[str, Any]]:
    """Reddit JSON 파일 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def cluster_locally(json_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """로컬에서 클러스터링 실행 (DB 연결 없이)"""
    print("=" * 80)
    print("로컬 클러스터링 실행")
    print("=" * 80)
    
    # 1. 카테고리별로 포스트 분류
    category_posts = {category: [] for category in CATEGORIES}
    
    for item in json_data:
        post_id = item.get('post_id')
        title = item.get('title', '')
        body = item.get('body', '')
        topic_category = item.get('topic_category')
        subreddit = item.get('subreddit')
        keyword = item.get('keyword')
        
        # 삭제된 글 스킵
        if is_deleted_post(title, body):
            continue
        
        # topic_category가 이미 있으면 그대로 사용
        if topic_category and topic_category in CATEGORIES:
            category = topic_category
        else:
            # 없으면 assign_post_to_category 사용
            post_text = extract_text_from_post(title, body)
            category = assign_post_to_category(post_text, keyword, subreddit)
            if category is None:
                continue
        
        # 코멘트 수 계산: comments 배열이 있으면 길이 사용, 없으면 num_comments 필드 사용
        comments = item.get('comments', [])
        num_comments = len(comments) if isinstance(comments, list) else item.get('num_comments', 0)
        
        category_posts[category].append({
            "post_id": post_id,
            "title": title,
            "body": body,
            "upvotes": item.get('upvotes', 0),
            "num_comments": num_comments,
            "text": extract_text_from_post(title, body),
            "subreddit": subreddit or "unknown",
            "topic_category": category
        })
    
    print(f"\n카테고리별 포스트 수:")
    for category, posts in category_posts.items():
        print(f"  {category}: {len(posts)}개")
    
    # 2. 각 카테고리별로 클러스터링 수행
    all_clusters = []
    
    for category in CATEGORIES:
        posts = category_posts[category]
        
        if len(posts) == 0:
            print(f"\n⚠️  {category}: 데이터 없음 (post 수: 0)")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"📌 {category} 클러스터링 시작 (포스트 수: {len(posts)})")
        print("=" * 80)
        
        # 각 카테고리 내에서 여러 sub-cluster 생성
        cluster_groups = cluster_posts_within_category(posts, category)
        
        print(f"생성된 sub-cluster 수: {len(cluster_groups)}")
        
        # 각 sub-cluster에 대해 처리
        for cluster_idx, cluster_group in enumerate(cluster_groups):
            cluster_label, cluster_posts = list(cluster_group.items())[0]
            
            if len(cluster_posts) == 0:
                continue
            
            # 대표 포스트 선택 (upvotes + num_comments 기준)
            posts_sorted = sorted(
                cluster_posts,
                key=lambda p: p['upvotes'] + p['num_comments'],
                reverse=True
            )
            representative_posts = posts_sorted[:min(10, len(posts_sorted))]
            
            # 상위 키워드 추출
            texts = [p['text'] for p in cluster_posts]
            top_keywords = extract_top_keywords(texts, top_n=20)
            
            # 클러스터 요약 생성
            summary = generate_cluster_summary(cluster_posts, top_keywords)
            
            # 클러스터 정보 저장
            cluster_info = {
                "cluster_id": f"{category}_{cluster_idx + 1}",
                "topic_category": category,
                "sub_cluster_index": cluster_idx,
                "size": len(cluster_posts),
                "post_ids": [p['post_id'] for p in cluster_posts],
                "representative_post_ids": [p['post_id'] for p in representative_posts],
                "top_keywords": [kw for kw, _ in top_keywords],
                "summary": summary,
                "posts": [
                    {
                        "post_id": p['post_id'],
                        "title": p['title'],
                        "body": p.get('body', ''),
                        "subreddit": p.get('subreddit', ''),
                        "upvotes": p['upvotes'],
                        "num_comments": p['num_comments']
                    }
                    for p in cluster_posts
                ]
            }
            
            all_clusters.append(cluster_info)
            
            print(f"  ✅ Sub-cluster {cluster_idx + 1}: {len(cluster_posts)} posts")
            print(f"     대표 키워드: {', '.join([kw for kw, _ in top_keywords[:5]])}")
    
    # 3. 결과를 JSON으로 저장
    result = {
        "metadata": {
            "total_posts": len(json_data),
            "total_clusters": len(all_clusters),
            "categories": {
                category: len(category_posts[category]) 
                for category in CATEGORIES
            }
        },
        "clusters": all_clusters
    }
    
    return result

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="로컬 클러스터링 실행 및 JSON 저장")
    parser.add_argument("input_json", help="입력 JSON 파일 경로")
    parser.add_argument("--output", "-o", default="clustering_results.json",
                       help="출력 JSON 파일 경로 (기본값: clustering_results.json)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    # JSON 파일 로드
    print(f"JSON 파일 로드 중: {input_path}")
    json_data = load_reddit_json(str(input_path))
    print(f"✅ {len(json_data)}개 포스트 로드 완료\n")
    
    # 클러스터링 실행
    result = cluster_locally(json_data)
    
    # JSON 파일로 저장
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("클러스터링 완료")
    print("=" * 80)
    print(f"\n결과 요약:")
    print(f"  - 전체 포스트 수: {result['metadata']['total_posts']}")
    print(f"  - 생성된 클러스터 수: {result['metadata']['total_clusters']}")
    print(f"\n카테고리별 클러스터 수:")
    for category in CATEGORIES:
        cluster_count = sum(1 for c in result['clusters'] if c['topic_category'] == category)
        post_count = result['metadata']['categories'].get(category, 0)
        print(f"  {category}: {post_count}개 포스트 → {cluster_count}개 클러스터")
    
    print(f"\n✅ 결과 저장 완료: {output_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
