"""
클러스터별 GPT 요약을 생성하여 DB에 저장하는 스크립트

사용법:
    python scripts/generate_gpt_summaries.py
    
모든 클러스터에 대해 GPT 요약을 생성하고 clusters 테이블의 summary 컬럼에 저장합니다.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from openai import OpenAI
from web.db_queries import get_db_connection

# .env 파일 로드
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

def generate_gpt_summary(cluster_data: Dict[str, Any]) -> Optional[str]:
    """
    GPT를 사용하여 클러스터 요약 생성
    
    Args:
        cluster_data: 클러스터 데이터
    
    Returns:
        GPT 생성 요약 텍스트
    """
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")
            return None
        
        client = OpenAI(api_key=openai_key)
        
        # 클러스터 정보 수집
        cluster_id = cluster_data.get("cluster_id", "Unknown")
        category = cluster_data.get("topic_category", "Unknown")
        top_keywords = cluster_data.get("top_keywords", [])[:10]
        posts = cluster_data.get("posts", [])[:5]  # 상위 5개 포스트만
        
        # 프롬프트 구성
        keywords_str = ", ".join(top_keywords) if top_keywords else "N/A"
        post_titles = [p.get("title", "") for p in posts if p.get("title")]
        post_titles_str = "\n".join([f"- {title}" for title in post_titles[:3]])
        
        prompt = f"""다음은 주방/요리 관련 Reddit 포스트 클러스터 정보입니다.

클러스터 ID: {cluster_id}
카테고리: {category}
주요 키워드: {keywords_str}

대표 포스트 제목:
{post_titles_str if post_titles_str else "N/A"}

이 클러스터의 핵심 주제와 주요 관심사가 무엇인지 2-3문장으로 간결하게 요약해주세요. 
한국어로 작성하고, 사용자들이 이 주제에 관심을 가질 만한 이유를 포함해주세요."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a content strategist analyzing kitchen lifestyle topics. Provide concise, insightful summaries in Korean."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        print(f"❌ GPT 요약 생성 실패 ({cluster_id}): {e}")
        return None

def update_cluster_summary_in_db(cluster_id: str, summary: str) -> bool:
    """
    DB의 clusters 테이블에 요약 저장
    
    Args:
        cluster_id: 클러스터 ID (문자열, 예: "SPRING_RECIPES_1")
        summary: 저장할 요약 텍스트
    
    Returns:
        성공 여부
    """
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        with conn.cursor() as cur:
            # cluster_id가 문자열인 경우 topic_category와 sub_cluster_index로 매칭
            if isinstance(cluster_id, str) and '_' in cluster_id:
                parts = cluster_id.rsplit('_', 1)
                if len(parts) == 2:
                    topic_category = parts[0]
                    try:
                        sub_cluster_index = int(parts[1]) - 1  # JSON은 1부터 시작, DB는 0부터 시작할 수 있음
                        cur.execute("""
                            UPDATE clusters
                            SET summary = %s
                            WHERE topic_category = %s 
                            AND sub_cluster_index = %s
                        """, (summary, topic_category, sub_cluster_index))
                        conn.commit()
                        return cur.rowcount > 0
                    except ValueError:
                        pass
            
            # 정수형 cluster_id로 직접 업데이트 시도
            try:
                cluster_id_int = int(cluster_id) if isinstance(cluster_id, str) else cluster_id
                cur.execute("""
                    UPDATE clusters
                    SET summary = %s
                    WHERE cluster_id = %s
                """, (summary, cluster_id_int))
                conn.commit()
                return cur.rowcount > 0
            except (ValueError, TypeError):
                pass
            
            return False
    except Exception as e:
        print(f"❌ DB 업데이트 실패 ({cluster_id}): {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """메인 함수: JSON 파일에서 클러스터를 읽어 GPT 요약 생성 후 DB에 저장"""
    json_path = project_root / "clustering_results.json"
    
    if not json_path.exists():
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        return
    
    print("📖 JSON 파일 로드 중...")
    with open(json_path, 'r', encoding='utf-8') as f:
        clustering_data = json.load(f)
    
    clusters = clustering_data.get("clusters", [])
    print(f"✅ {len(clusters)}개 클러스터 발견")
    
    # 진행 상황 추적
    total = len(clusters)
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for idx, cluster in enumerate(clusters, 1):
        cluster_id = cluster.get("cluster_id", "Unknown")
        print(f"\n[{idx}/{total}] 처리 중: {cluster_id}")
        
        # 이미 요약이 있는지 확인
        existing_summary = None
        try:
            from web.db_queries import get_cluster_summary_from_db
            existing_summary = get_cluster_summary_from_db(cluster_id)
        except:
            pass
        
        if existing_summary:
            print(f"  ⏭️  이미 요약이 존재합니다. 건너뜁니다.")
            skip_count += 1
            continue
        
        # GPT 요약 생성
        print(f"  🤖 GPT 요약 생성 중...")
        summary = generate_gpt_summary(cluster)
        
        if summary:
            # DB에 저장
            print(f"  💾 DB에 저장 중...")
            if update_cluster_summary_in_db(cluster_id, summary):
                print(f"  ✅ 완료: {summary[:50]}...")
                success_count += 1
            else:
                print(f"  ❌ DB 저장 실패")
                error_count += 1
        else:
            print(f"  ❌ 요약 생성 실패")
            error_count += 1
    
    # 최종 결과
    print("\n" + "="*50)
    print("📊 최종 결과")
    print("="*50)
    print(f"✅ 성공: {success_count}개")
    print(f"⏭️  건너뜀: {skip_count}개")
    print(f"❌ 실패: {error_count}개")
    print(f"📝 총 처리: {total}개")

if __name__ == "__main__":
    main()
