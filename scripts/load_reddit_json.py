#!/usr/bin/env python3
"""
Reddit JSON 파일 적재 스크립트

기존 Reddit 데이터를 모두 삭제하고 새로운 JSON 파일을 적재합니다.
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.logging import setup_logger
from psycopg2.extras import Json as PsycopgJson

logger = setup_logger("load_reddit_json")

def delete_all_reddit_data():
    """기존 Reddit 데이터 모두 삭제"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            logger.info("기존 Reddit 데이터 삭제 중...")
            
            # Foreign key 제약 조건 때문에 순서 중요
            # 1. Comments 삭제
            cur.execute("DELETE FROM raw_reddit_comments")
            comments_deleted = cur.rowcount
            
            # 2. Posts 삭제
            cur.execute("DELETE FROM raw_reddit_posts")
            posts_deleted = cur.rowcount
            
            # 3. 관련된 클러스터 데이터도 삭제 (선택사항)
            cur.execute("DELETE FROM cluster_assignments WHERE doc_type = 'reddit_post'")
            assignments_deleted = cur.rowcount
            
            cur.execute("DELETE FROM clusters WHERE algorithm IN ('TF-IDF_KEYWORD', 'TF-IDF_KMEANS')")
            clusters_deleted = cur.rowcount
            
            conn.commit()
            
            logger.info(f"삭제 완료:")
            logger.info(f"  - Comments: {comments_deleted}개")
            logger.info(f"  - Posts: {posts_deleted}개")
            logger.info(f"  - Cluster assignments: {assignments_deleted}개")
            logger.info(f"  - Clusters: {clusters_deleted}개")
            
            return True
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"데이터 삭제 실패: {e}", exc_info=True)
        raise
    finally:
        if conn:
            put_db_connection(conn)

def load_reddit_json(json_path: str):
    """JSON 파일에서 Reddit 데이터 적재"""
    logger.info(f"JSON 파일 로드 중: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"총 {len(data)}개 포스트 발견")
    
    conn = None
    stats = {
        "posts_inserted": 0,
        "posts_skipped": 0,
        "comments_inserted": 0,
        "errors": []
    }
    
    try:
        conn = get_db_connection()
        
        # topic_category별 통계
        category_stats = {}
        
        for idx, item in enumerate(data):
            try:
                # JSON 구조: post_id, topic_category, title, body, comments, created_at
                post_id = item.get('post_id')
                topic_category = item.get('topic_category')
                title = item.get('title', '')
                body = item.get('body', '')
                comments = item.get('comments', [])
                created_at_str = item.get('created_at')
                
                # 필수 필드 검증
                if not post_id or not title:
                    logger.warning(f"포스트 {idx+1}: 필수 필드 누락 (post_id={post_id}, title={bool(title)})")
                    stats["posts_skipped"] += 1
                    continue
                
                # topic_category 통계
                if topic_category:
                    category_stats[topic_category] = category_stats.get(topic_category, 0) + 1
                
                # created_at 파싱
                created_utc = None
                if created_at_str:
                    try:
                        # ISO 형식 또는 타임스탬프로 파싱 시도
                        if isinstance(created_at_str, (int, float)):
                            created_utc = int(created_at_str)
                        else:
                            dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            created_utc = int(dt.timestamp())
                    except:
                        created_utc = int(datetime.now().timestamp())
                else:
                    created_utc = int(datetime.now().timestamp())
                
                # subreddit 추정 (topic_category 기반)
                # JSON에 subreddit이 없으면 topic_category 기반으로 추정
                subreddit = item.get('subreddit')
                if not subreddit:
                    # topic_category 기반으로 subreddit 추정
                    if topic_category == "SPRING_RECIPES":
                        subreddit = "cooking"
                    elif topic_category == "SPRING_KITCHEN_STYLING":
                        subreddit = "interiordesign"
                    elif topic_category == "REFRIGERATOR_ORGANIZATION":
                        subreddit = "organization"
                    elif topic_category == "VEGETABLE_PREP_HANDLING":
                        subreddit = "mealprep"
                    else:
                        subreddit = "cooking"  # 기본값
                
                # keyword는 topic_category를 사용하거나 title에서 추출
                keyword = item.get('keyword')
                if not keyword:
                    # title에서 첫 번째 단어를 keyword로 사용
                    keyword = title.split()[0] if title else topic_category or "unknown"
                
                # 포스트 저장
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO raw_reddit_posts (
                            reddit_post_id, subreddit, title, body, author,
                            created_utc, upvotes, num_comments, permalink, url,
                            keyword, raw_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (reddit_post_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            body = EXCLUDED.body,
                            upvotes = EXCLUDED.upvotes,
                            num_comments = EXCLUDED.num_comments,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        post_id,
                        subreddit,
                        title,
                        body,
                        item.get('author'),  # None 가능
                        created_utc,
                        item.get('upvotes', 0),
                        item.get('num_comments', len(comments)),  # comments 수를 num_comments로 사용
                        item.get('permalink'),
                        item.get('url'),
                        keyword,
                        PsycopgJson(item)  # 전체 JSON 저장
                    ))
                    
                    stats["posts_inserted"] += 1
                    
                    # 댓글 저장
                    for comment in comments:
                        comment_id = comment.get('comment_id')
                        comment_text = comment.get('text', '')
                        
                        if not comment_id or not comment_text:
                            continue
                        
                        try:
                            cur.execute("""
                                INSERT INTO raw_reddit_comments (
                                    reddit_comment_id, reddit_post_id, author, body,
                                    created_utc, upvotes, is_top, raw_json
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (reddit_comment_id) DO UPDATE SET
                                    body = EXCLUDED.body,
                                    upvotes = EXCLUDED.upvotes,
                                    updated_at = CURRENT_TIMESTAMP
                            """, (
                                comment_id,
                                post_id,
                                comment.get('author'),
                                comment_text,
                                comment.get('created_utc', created_utc),
                                comment.get('upvotes', 0),
                                comment.get('is_top', False),
                                PsycopgJson(comment)
                            ))
                            stats["comments_inserted"] += 1
                        except Exception as e:
                            logger.warning(f"댓글 저장 실패 (comment_id={comment_id}): {e}")
                            stats["errors"].append(f"comment_{comment_id}: {str(e)}")
                
                # 배치 커밋 (100개마다)
                if (idx + 1) % 100 == 0:
                    conn.commit()
                    logger.info(f"진행: {idx+1}/{len(data)} 포스트 저장됨")
            
            except Exception as e:
                logger.error(f"포스트 저장 실패 (post_id={item.get('post_id')}): {e}", exc_info=True)
                stats["errors"].append(f"post_{item.get('post_id')}: {str(e)}")
                stats["posts_skipped"] += 1
                continue
        
        # 최종 커밋
        conn.commit()
        
        logger.info("=" * 80)
        logger.info("적재 완료")
        logger.info("=" * 80)
        logger.info(f"포스트 삽입: {stats['posts_inserted']}개")
        logger.info(f"포스트 스킵: {stats['posts_skipped']}개")
        logger.info(f"댓글 삽입: {stats['comments_inserted']}개")
        logger.info(f"에러: {len(stats['errors'])}개")
        
        logger.info("\ntopic_category별 통계:")
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {category}: {count}개")
        
        return stats
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"데이터 적재 실패: {e}", exc_info=True)
        raise
    finally:
        if conn:
            put_db_connection(conn)

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reddit JSON 파일 적재")
    parser.add_argument("json_file", help="적재할 JSON 파일 경로")
    parser.add_argument("--no-delete", action="store_true", 
                       help="기존 데이터 삭제하지 않음")
    
    args = parser.parse_args()
    
    json_path = Path(args.json_file)
    if not json_path.exists():
        logger.error(f"파일을 찾을 수 없습니다: {json_path}")
        sys.exit(1)
    
    try:
        # 1. 기존 데이터 삭제
        if not args.no_delete:
            logger.info("=" * 80)
            logger.info("1단계: 기존 데이터 삭제")
            logger.info("=" * 80)
            delete_all_reddit_data()
        else:
            logger.info("기존 데이터 삭제 스킵 (--no-delete 옵션)")
        
        # 2. 새 데이터 적재
        logger.info("")
        logger.info("=" * 80)
        logger.info("2단계: 새 데이터 적재")
        logger.info("=" * 80)
        stats = load_reddit_json(str(json_path))
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("완료!")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"실행 실패: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
