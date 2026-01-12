"""
마스터 토픽 JSON 내용을 콘솔에 출력하는 스크립트
"""
import json
from pathlib import Path

def print_master_topics():
    """마스터 토픽 JSON을 읽어서 콘솔에 출력"""
    project_root = Path(__file__).parent
    json_path = project_root / "data" / "master_topics_final_kr_en_RICH_WHY.json"
    
    if not json_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {json_path}")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 파일 로드 오류: {e}")
        return
    
    print("=" * 80)
    print("🏠 LG전자 HS 마스터 토픽 제안")
    print("=" * 80)
    print()
    
    categories = [
        "SPRING_RECIPES",
        "REFRIGERATOR_ORGANIZATION",
        "VEGETABLE_PREP_HANDLING",
        "SPRING_KITCHEN_STYLING"
    ]
    
    for category in categories:
        if category not in data:
            continue
        
        topics = data[category]
        print(f"\n{'=' * 80}")
        print(f"📌 {category} ({len(topics)} topics)")
        print(f"{'=' * 80}\n")
        
        for idx, topic in enumerate(topics, start=1):
            print(f"[{idx}] {topic.get('master_topic_kr', 'N/A')}")
            print(f"    ({topic.get('master_topic_en', 'N/A')})")
            print()
            
            why_now_kr = topic.get('why_now_kr', '')
            if why_now_kr:
                print(f"    Why Now (KR):")
                print(f"    {why_now_kr}")
                print()
            
            why_now_en = topic.get('why_now_en', '')
            if why_now_en:
                print(f"    Why Now (EN):")
                print(f"    {why_now_en}")
                print()
            
            content_angle = topic.get('content_angle', '')
            if content_angle:
                print(f"    Content Angle: • {content_angle}")
            
            print()
            print("-" * 80)
            print()
    
    print("=" * 80)
    print(f"총 {sum(len(data.get(cat, [])) for cat in categories)}개 토픽")
    print("=" * 80)

if __name__ == "__main__":
    print_master_topics()
