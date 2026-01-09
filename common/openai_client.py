"""
OpenAI API 클라이언트 통합 모듈

목적: 모든 GPT 호출에서 사용할 단일 OpenAI 클라이언트 제공
- API 키는 앱 시작 시 1회만 로드
- 키가 없으면 명확한 에러 메시지 출력
- 재사용 가능한 싱글톤 패턴
"""
import os
from typing import Optional
from openai import OpenAI
from pathlib import Path

# 전역 클라이언트 인스턴스 (싱글톤)
_client: Optional[OpenAI] = None
_api_key: Optional[str] = None


def load_openai_api_key() -> Optional[str]:
    """
    OpenAI API 키 로드 (우선순위: 환경변수 > .env 파일)
    
    Returns:
        API 키 문자열 또는 None
    """
    # 1순위: 환경변수 (Railway 등 배포 환경에서 사용)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.strip() and api_key != "your_openai_api_key":
        return api_key.strip()
    
    # 2순위: .env 파일 (로컬 개발용)
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    
    # dotenv를 사용하여 .env 파일 로드
    try:
        from dotenv import load_dotenv
        if env_path.exists():
            # override=False: 환경 변수가 이미 있으면 덮어쓰지 않음
            load_dotenv(dotenv_path=env_path, override=False)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key and api_key.strip() and api_key != "your_openai_api_key":
                return api_key.strip()
    except ImportError:
        # dotenv가 없으면 .env 파일을 직접 읽기
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == "OPENAI_API_KEY" and value and value != "your_openai_api_key":
                            # 환경 변수에 직접 설정
                            os.environ["OPENAI_API_KEY"] = value
                            return value
    
    return None


def get_openai_client() -> OpenAI:
    """
    OpenAI 클라이언트 싱글톤 인스턴스 반환
    
    Returns:
        OpenAI 클라이언트 인스턴스
        
    Raises:
        ValueError: API 키가 설정되지 않은 경우
    """
    global _client, _api_key
    
    # 이미 생성된 클라이언트가 있으면 재사용
    if _client is not None:
        return _client
    
    # API 키 로드
    if _api_key is None:
        _api_key = load_openai_api_key()
    
    if not _api_key:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않았습니다.\n"
            "환경변수 또는 .env 파일에 OPENAI_API_KEY를 설정하세요."
        )
    
    # 클라이언트 생성
    _client = OpenAI(api_key=_api_key)
    return _client


def reset_client():
    """클라이언트 리셋 (테스트용)"""
    global _client, _api_key
    _client = None
    _api_key = None


def is_openai_available() -> bool:
    """OpenAI API 키가 사용 가능한지 확인"""
    global _api_key
    try:
        if _api_key is None:
            _api_key = load_openai_api_key()
        # API 키가 있고 비어있지 않은지 확인
        if _api_key is None:
            return False
        api_key_stripped = _api_key.strip()
        return len(api_key_stripped) > 0
    except Exception as e:
        # 디버깅을 위해 예외 정보 출력 (선택사항)
        import sys
        print(f"Warning: is_openai_available() error: {e}", file=sys.stderr)
        return False
