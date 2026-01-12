#!/usr/bin/env python3
"""SERP AI Overview의 키워드(쿼리) 리스트만 출력"""
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

from web.db_queries import get_serp_aio

print("=" * 80)
print("SERP AI Overview 키워드 리스트")
print("=" * 80)
print()

try:
    # SERP AI Overview 데이터 조회
    serp_df = get_serp_aio()
    
    if len(serp_df) == 0:
        print("⚠️ SERP AI Overview 데이터가 없습니다.")
        sys.exit(1)
    
    # Error 제외하고 AVAILABLE, NOT_AVAILABLE만 필터링
    filtered_df = serp_df[serp_df['aio_status'].isin(['AVAILABLE', 'NOT_AVAILABLE'])].copy()
    
    # 쿼리(키워드) 목록 추출
    keywords = filtered_df['query'].dropna().unique().tolist()
    keywords = sorted([k for k in keywords if k and k.strip()])  # 빈 값 제거 및 정렬
    
    print(f"총 {len(keywords)}개 키워드\n")
    print("=" * 80)
    print()
    
    # 키워드 리스트 출력
    for idx, keyword in enumerate(keywords, 1):
        print(f"{idx}. {keyword}")
    
    print()
    print("=" * 80)
    print(f"총 {len(keywords)}개 키워드")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
