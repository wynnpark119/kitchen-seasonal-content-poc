"""
Worker 메인 스크립트
데이터 수집/분석 파이프라인 실행
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Worker 메인 함수"""
    print("Worker 시작 - 데이터 파이프라인 구현 예정")
    print("SPEC.md를 참고하여 개발하세요.")
    
    # TODO: 데이터 수집/분석 파이프라인 구현
    pass

if __name__ == "__main__":
    main()
