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
    # 1순위: 환경변수
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key.strip()
    
    # 2순위: .env 파일
    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                return api_key.strip()
    except ImportError:
        # dotenv가 없으면 .env 파일을 직접 읽기
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == "OPENAI_API_KEY" and value:
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
    try:
        if _api_key is None:
            _api_key = load_openai_api_key()
        return _api_key is not None and len(_api_key.strip()) > 0
    except Exception:
        return False
