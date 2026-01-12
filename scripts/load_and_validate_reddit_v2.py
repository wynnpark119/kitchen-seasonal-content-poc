#!/usr/bin/env python3
"""
Reddit JSON v2 파일 적재 및 검증 스크립트

topic_category가 이미 확정된 정제된 입력 데이터를 DB에 적재하고 검증합니다.
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter, defaultdict

# .env 파일 로드 (db.py와 동일한 방식)
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()  # 시스템 환경 변수만 로드
except ImportError:
    # dotenv가 없으면 직접 읽기
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not os.getenv(key):
                            os.environ[key] = value
        except (PermissionError, IOError):
            pass

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import get_db_connection, put_db_connection
from worker.pipeline.logging import setup_logger
from psycopg2.extras import Json as PsycopgJson, execute_batch

logger = setup_logger("load_reddit_v2")

def check_json_structure(json_path: str):
    """[1] 입력 파일 확인"""
    print("=" * 80)
    print("[1] 입력 파일 확인")
    print("=" * 80)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError(f"JSON 파일은 리스트 형태여야 합니다. 현재 타입: {type(data)}")
    
    total_posts = len(data)
    print(f"\n총 post 수: {total_posts}")
    
    # topic_category별 통계
    category_counts = Counter()
    for item in data:
        category = item.get('topic_category', 'UNKNOWN')
        category_counts[category] += 1
    
    print(f"\ntopic_category별 post 수:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count}개")
    
    # 첫 번째 항목 구조 확인
    if len(data) > 0:
        sample = data[0]
        print(f"\n샘플 항목 구조:")
        print(f"  키: {list(sample.keys())}")
        if 'comments' in sample:
            print(f"  comments 수: {len(sample.get('comments', []))}")
            if len(sample.get('comments', [])) > 0:
                print(f"  첫 번째 comment 키: {list(sample['comments'][0].keys())}")
    
    return data, category_counts

def check_db_tables():
    """[2] 적재 대상 DB 테이블 확인"""
    print("\n" + "=" * 80)
    print("[2] 적재 대상 DB 테이블 확인")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # raw_reddit_posts 테이블 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'raw_reddit_posts'
                ORDER BY ordinal_position
            """)
            
            post_columns = cur.fetchall()
            print("\nraw_reddit_posts 테이블 컬럼:")
            for col_name, data_type, is_nullable in post_columns:
                print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")
            
            # raw_reddit_comments 테이블 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'raw_reddit_comments'
                ORDER BY ordinal_position
            """)
            
            comment_columns = cur.fetchall()
            print("\nraw_reddit_comments 테이블 컬럼:")
            for col_name, data_type, is_nullable in comment_columns:
                print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")
            
            # topic_category 컬럼이 있는지 확인
            post_col_names = [col[0] for col in post_columns]
            if 'topic_category' not in post_col_names:
                print("\n⚠️  topic_category 컬럼이 없습니다. 추가가 필요할 수 있습니다.")
                return False
            
            return True
    
    finally:
        if conn:
            put_db_connection(conn)

def add_topic_category_column_if_needed():
    """topic_category 컬럼이 없으면 추가"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 컬럼 존재 여부 확인
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'raw_reddit_posts'
                AND column_name = 'topic_category'
            """)
            
            if cur.fetchone() is None:
                print("\ntopic_category 컬럼 추가 중...")
                cur.execute("""
                    ALTER TABLE raw_reddit_posts
                    ADD COLUMN topic_category VARCHAR(50)
                """)
                conn.commit()
                print("✅ topic_category 컬럼 추가 완료")
                return True
            else:
                print("\n✅ topic_category 컬럼 이미 존재")
                return False
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"컬럼 추가 실패: {e}", exc_info=True)
        raise
    finally:
        if conn:
            put_db_connection(conn)

def load_posts_and_comments(data: List[Dict[str, Any]]):
    """[3] 적재 로직 구현"""
    print("\n" + "=" * 80)
    print("[3] 적재 로직 구현 및 실행")
    print("=" * 80)
    
    conn = None
    stats = {
        "posts_inserted": 0,
        "posts_updated": 0,
        "posts_skipped": 0,
        "comments_inserted": 0,
        "comments_updated": 0,
        "comments_skipped": 0,
        "errors": [],
        "category_stats": defaultdict(lambda: {"inserted": 0, "updated": 0})
    }
    
    try:
        conn = get_db_connection()
        
        # 배치 처리용 데이터
        posts_batch = []
        comments_batch = []
        batch_size = 200
        
        for idx, item in enumerate(data):
            try:
                post_id = item.get('post_id')
                topic_category = item.get('topic_category')
                title = item.get('title', '')
                body = item.get('body', '')
                comments = item.get('comments', [])
                created_at_str = item.get('created_at')
                
                # 필수 필드 검증
                if not post_id:
                    logger.warning(f"포스트 {idx+1}: post_id 누락")
                    stats["posts_skipped"] += 1
                    continue
                
                if not title:
                    logger.warning(f"포스트 {post_id}: title 누락")
                    stats["posts_skipped"] += 1
                    continue
                
                # created_at 파싱
                created_utc = None
                if created_at_str:
                    try:
                        if isinstance(created_at_str, (int, float)):
                            created_utc = int(created_at_str)
                        else:
                            dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            created_utc = int(dt.timestamp())
                    except Exception as e:
                        logger.warning(f"포스트 {post_id}: created_at 파싱 실패 ({created_at_str}), 현재 시간 사용")
                        created_utc = int(datetime.now().timestamp())
                else:
                    created_utc = int(datetime.now().timestamp())
                
                # subreddit 추정 (topic_category 기반)
                subreddit = item.get('subreddit')
                if not subreddit:
                    if topic_category == "SPRING_RECIPES":
                        subreddit = "cooking"
                    elif topic_category == "SPRING_KITCHEN_STYLING":
                        subreddit = "interiordesign"
                    elif topic_category == "REFRIGERATOR_ORGANIZATION":
                        subreddit = "organization"
                    elif topic_category == "VEGETABLE_PREP_HANDLING":
                        subreddit = "mealprep"
                    else:
                        subreddit = "cooking"
                
                # keyword는 title에서 추출하거나 topic_category 사용
                keyword = item.get('keyword')
                if not keyword:
                    keyword = title.split()[0] if title else topic_category or "unknown"
                
                # 포스트 데이터 준비
                posts_batch.append((
                    post_id,
                    subreddit[:100],
                    title[:10000],  # TEXT 타입이지만 안전을 위해 제한
                    body[:50000] if body else None,
                    item.get('author'),
                    created_utc,
                    item.get('upvotes', 0),
                    item.get('num_comments', len(comments)),
                    item.get('permalink'),
                    item.get('url'),
                    keyword[:200],
                    topic_category,  # topic_category 추가
                    PsycopgJson(item)  # raw_json
                ))
                
                # 댓글 데이터 준비
                for comment in comments[:3]:  # 최대 3개
                    comment_id = comment.get('comment_id')
                    comment_text = comment.get('text', '')
                    
                    if not comment_id or not comment_text:
                        continue
                    
                    comments_batch.append((
                        comment_id,
                        post_id,  # FK
                        comment.get('author'),
                        comment_text[:50000],
                        comment.get('created_utc', created_utc),
                        comment.get('upvotes', 0),
                        comment.get('is_top', False),
                        PsycopgJson(comment)
                    ))
                
                # 배치 크기 도달 시 실행
                if len(posts_batch) >= batch_size:
                    _insert_batch(conn, posts_batch, comments_batch, stats)
                    posts_batch = []
                    comments_batch = []
                    logger.info(f"진행: {idx+1}/{len(data)} 포스트 처리됨")
            
            except Exception as e:
                logger.error(f"포스트 처리 실패 (post_id={item.get('post_id')}): {e}", exc_info=True)
                stats["errors"].append(f"post_{item.get('post_id')}: {str(e)}")
                stats["posts_skipped"] += 1
                continue
        
        # 남은 배치 처리
        if posts_batch:
            _insert_batch(conn, posts_batch, comments_batch, stats)
        
        conn.commit()
        
        # [4] 적재 실행 로그 출력
        print("\n" + "=" * 80)
        print("[4] 적재 실행 로그")
        print("=" * 80)
        print(f"\n전체 처리 post 수: {len(data)}")
        print(f"포스트 삽입: {stats['posts_inserted']}개")
        print(f"포스트 업데이트: {stats['posts_updated']}개")
        print(f"포스트 스킵: {stats['posts_skipped']}개")
        print(f"댓글 삽입: {stats['comments_inserted']}개")
        print(f"댓글 업데이트: {stats['comments_updated']}개")
        print(f"댓글 스킵: {stats['comments_skipped']}개")
        print(f"에러: {len(stats['errors'])}개")
        
        print("\ntopic_category별 insert/update 수:")
        for category, cat_stats in sorted(stats['category_stats'].items()):
            print(f"  {category}:")
            print(f"    - inserted: {cat_stats['inserted']}개")
            print(f"    - updated: {cat_stats['updated']}개")
        
        return stats
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"데이터 적재 실패: {e}", exc_info=True)
        raise
    finally:
        if conn:
            put_db_connection(conn)

def _insert_batch(conn, posts_batch: List, comments_batch: List, stats: Dict):
    """배치 INSERT 실행"""
    with conn.cursor() as cur:
        # 포스트 배치 INSERT
        if posts_batch:
            try:
                execute_batch(cur, """
                    INSERT INTO raw_reddit_posts (
                        reddit_post_id, subreddit, title, body, author,
                        created_utc, upvotes, num_comments, permalink, url,
                        keyword, topic_category, raw_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reddit_post_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        body = EXCLUDED.body,
                        topic_category = EXCLUDED.topic_category,
                        upvotes = EXCLUDED.upvotes,
                        num_comments = EXCLUDED.num_comments,
                        updated_at = CURRENT_TIMESTAMP
                """, posts_batch, page_size=100)
                
                # 통계 업데이트 (간단히 전체를 inserted로 처리, 실제로는 RETURNING으로 확인 필요)
                for post_data in posts_batch:
                    topic_category = post_data[11]  # topic_category 위치
                    if topic_category:
                        stats['category_stats'][topic_category]['inserted'] += 1
                
                stats["posts_inserted"] += len(posts_batch)
                
            except Exception as e:
                logger.error(f"포스트 배치 INSERT 실패: {e}", exc_info=True)
                raise
        
        # 댓글 배치 INSERT (포스트가 먼저 저장된 후)
        if comments_batch:
            try:
                execute_batch(cur, """
                    INSERT INTO raw_reddit_comments (
                        reddit_comment_id, reddit_post_id, author, body,
                        created_utc, upvotes, is_top, raw_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reddit_comment_id) DO UPDATE SET
                        body = EXCLUDED.body,
                        upvotes = EXCLUDED.upvotes,
                        updated_at = CURRENT_TIMESTAMP
                """, comments_batch, page_size=100)
                
                stats["comments_inserted"] += len(comments_batch)
                
            except Exception as e:
                logger.error(f"댓글 배치 INSERT 실패: {e}", exc_info=True)
                # FK 제약 조건 위반 체크
                if "foreign key" in str(e).lower():
                    logger.error("⚠️  FK 제약 조건 위반: 댓글의 post_id가 posts 테이블에 존재하지 않습니다!")
                raise
        
        conn.commit()

def validate_db_results(json_data: List[Dict[str, Any]]):
    """[5] DB 적재 결과 검증"""
    print("\n" + "=" * 80)
    print("[5] DB 적재 결과 검증")
    print("=" * 80)
    
    conn = None
    issues = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # A) 전체 post 수 확인
            cur.execute("SELECT COUNT(*) FROM raw_reddit_posts")
            db_post_count = cur.fetchone()[0]
            json_post_count = len(json_data)
            
            print(f"\nA) 전체 post 수:")
            print(f"   JSON 파일: {json_post_count}개")
            print(f"   DB: {db_post_count}개")
            
            if db_post_count != json_post_count:
                issues.append(f"전체 post 수 불일치: JSON={json_post_count}, DB={db_post_count}")
            else:
                print(f"   ✅ 일치")
            
            # B) topic_category별 post 수 분포
            print(f"\nB) topic_category별 post 수 분포:")
            print(f"{'Topic':<40} | {'Posts':<10} | {'Comments':<10}")
            print("-" * 65)
            
            cur.execute("""
                SELECT topic_category, COUNT(*) as post_count
                FROM raw_reddit_posts
                WHERE topic_category IS NOT NULL
                GROUP BY topic_category
                ORDER BY post_count DESC
            """)
            
            db_category_counts = {}
            for category, count in cur.fetchall():
                db_category_counts[category] = count
                print(f"{category:<40} | {count:<10} | ", end="")
                
                # 댓글 수 조회
                cur.execute("""
                    SELECT COUNT(*)
                    FROM raw_reddit_comments rc
                    JOIN raw_reddit_posts rp ON rc.reddit_post_id = rp.reddit_post_id
                    WHERE rp.topic_category = %s
                """, (category,))
                comment_count = cur.fetchone()[0]
                print(f"{comment_count:<10}")
            
            # JSON과 비교
            json_category_counts = Counter(item.get('topic_category') for item in json_data)
            for category, json_count in json_category_counts.items():
                db_count = db_category_counts.get(category, 0)
                if db_count != json_count:
                    issues.append(f"{category} post 수 불일치: JSON={json_count}, DB={db_count}")
            
            # C) post당 comment 수 분포
            print(f"\nC) post당 comment 수 분포:")
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT rp.reddit_post_id) as posts_with_comments,
                    COALESCE(SUM(comment_count), 0) as total_comments,
                    ROUND(AVG(comment_count), 2) as avg_comments,
                    MAX(comment_count) as max_comments
                FROM raw_reddit_posts rp
                LEFT JOIN (
                    SELECT reddit_post_id, COUNT(*) as comment_count
                    FROM raw_reddit_comments
                    GROUP BY reddit_post_id
                ) rc ON rp.reddit_post_id = rc.reddit_post_id
            """)
            
            result = cur.fetchone()
            if result:
                posts_with_comments, total_comments, avg_comments, max_comments = result
                print(f"   댓글이 있는 포스트: {posts_with_comments}개")
                print(f"   전체 댓글 수: {total_comments}개")
                print(f"   평균 댓글 수: {avg_comments}개")
                print(f"   최대 댓글 수: {max_comments}개")
                
                if max_comments and max_comments > 3:
                    issues.append(f"최대 댓글 수가 3개를 초과: {max_comments}개")
                else:
                    print(f"   ✅ 최대 댓글 수 3개 이하")
            
            # D) orphan comment 확인
            print(f"\nD) orphan comment 확인:")
            cur.execute("""
                SELECT COUNT(*)
                FROM raw_reddit_comments rc
                LEFT JOIN raw_reddit_posts rp ON rc.reddit_post_id = rp.reddit_post_id
                WHERE rp.reddit_post_id IS NULL
            """)
            
            orphan_count = cur.fetchone()[0]
            print(f"   orphan comment 수: {orphan_count}개")
            
            if orphan_count > 0:
                issues.append(f"orphan comment 발견: {orphan_count}개")
            else:
                print(f"   ✅ orphan comment 없음")
            
            return len(issues) == 0, issues
    
    finally:
        if conn:
            put_db_connection(conn)

def validate_samples():
    """[6] 샘플 검증"""
    print("\n" + "=" * 80)
    print("[6] 샘플 검증")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 각 topic_category별로 랜덤 3개 포스트 선택
            cur.execute("""
                SELECT DISTINCT topic_category
                FROM raw_reddit_posts
                WHERE topic_category IS NOT NULL
                ORDER BY topic_category
            """)
            
            categories = [row[0] for row in cur.fetchall()]
            
            for category in categories:
                print(f"\n{'=' * 80}")
                print(f"Topic: {category}")
                print("=" * 80)
                
                cur.execute("""
                    SELECT rp.reddit_post_id, rp.title, rp.created_at,
                           rp.topic_category
                    FROM raw_reddit_posts rp
                    WHERE rp.topic_category = %s
                    ORDER BY RANDOM()
                    LIMIT 3
                """, (category,))
                
                posts = cur.fetchall()
                
                for i, (post_id, title, created_at, topic_cat) in enumerate(posts, 1):
                    print(f"\n  포스트 {i}:")
                    print(f"    post_id: {post_id}")
                    print(f"    title: {title[:80]}...")
                    print(f"    created_at: {created_at}")
                    print(f"    topic_category: {topic_cat}")
                    
                    # 댓글 1~2개 조회
                    cur.execute("""
                        SELECT body
                        FROM raw_reddit_comments
                        WHERE reddit_post_id = %s
                        ORDER BY upvotes DESC
                        LIMIT 2
                    """, (post_id,))
                    
                    comments = cur.fetchall()
                    if comments:
                        print(f"    댓글:")
                        for j, (comment_text,) in enumerate(comments, 1):
                            print(f"      {j}. {comment_text[:100]}...")
                    else:
                        print(f"    댓글: 없음")
    
    finally:
        if conn:
            put_db_connection(conn)

def final_judgment(validation_ok: bool, issues: List[str], stats: Dict):
    """[7] 최종 판정"""
    print("\n" + "=" * 80)
    print("[7] 최종 판정")
    print("=" * 80)
    
    db_success = stats['posts_inserted'] > 0 and len(stats['errors']) == 0
    data_integrity = validation_ok
    
    print(f"\n검증 결과:")
    print(f"  - DB 적재 성공 여부: {'SUCCESS' if db_success else 'FAIL'}")
    print(f"  - 데이터 무결성: {'PASS' if data_integrity else 'FAIL'}")
    
    can_proceed = db_success and data_integrity
    
    print(f"  - 다음 단계(주제별 sub-cluster 클러스터링) 진행 가능 여부: {'YES' if can_proceed else 'NO'}")
    
    if not db_success:
        print(f"\n⚠️  DB 적재 실패:")
        print(f"   - 삽입된 포스트: {stats['posts_inserted']}개")
        print(f"   - 에러 수: {len(stats['errors'])}개")
        if stats['errors']:
            for error in stats['errors'][:5]:
                print(f"     - {error}")
    
    if not data_integrity:
        print(f"\n⚠️  데이터 무결성 문제:")
        for issue in issues:
            print(f"   - {issue}")
    
    if not can_proceed:
        print(f"\n수정 필요 사항:")
        if not db_success:
            print(f"   1. DB 적재 로직 확인: scripts/load_and_validate_reddit_v2.py")
            print(f"   2. 에러 메시지 확인 및 수정")
        if not data_integrity:
            print(f"   3. 데이터 검증 로직 확인")
            print(f"   4. FK 제약 조건 확인")
    
    return can_proceed

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reddit JSON v2 파일 적재 및 검증")
    parser.add_argument("json_file", help="적재할 JSON 파일 경로")
    parser.add_argument("--no-delete", action="store_true", 
                       help="기존 데이터 삭제하지 않음")
    
    args = parser.parse_args()
    
    json_path = Path(args.json_file)
    if not json_path.exists():
        logger.error(f"파일을 찾을 수 없습니다: {json_path}")
        sys.exit(1)
    
    try:
        # [1] 입력 파일 확인
        json_data, category_counts = check_json_structure(str(json_path))
        
        # [2] DB 테이블 확인
        tables_ok = check_db_tables()
        
        # topic_category 컬럼 추가 (필요시)
        add_topic_category_column_if_needed()
        
        # 기존 데이터 삭제 (선택사항)
        if not args.no_delete:
            print("\n" + "=" * 80)
            print("기존 Reddit 데이터 삭제")
            print("=" * 80)
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM raw_reddit_comments")
                    cur.execute("DELETE FROM raw_reddit_posts")
                    conn.commit()
                    print("✅ 기존 데이터 삭제 완료")
            finally:
                if conn:
                    put_db_connection(conn)
        
        # [3] 적재 로직 실행
        stats = load_posts_and_comments(json_data)
        
        # [5] DB 적재 결과 검증
        validation_ok, issues = validate_db_results(json_data)
        
        # [6] 샘플 검증
        validate_samples()
        
        # [7] 최종 판정
        can_proceed = final_judgment(validation_ok, issues, stats)
        
        return 0 if can_proceed else 1
    
    except Exception as e:
        logger.error(f"실행 실패: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
