"""
경로 유틸리티 모듈

프로젝트 루트와 데이터 폴더 경로를 안정적으로 계산하는 유틸리티
로컬/서버 환경에서 모두 동작하도록 설계됨
"""
import os
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# 전역 캐시
_project_root: Optional[Path] = None
_data_dir: Optional[Path] = None


def get_project_root() -> Path:
    """
    프로젝트 루트 경로를 안정적으로 계산
    
    계산 순서:
    1. 환경 변수 PROJECT_ROOT (명시적 설정)
    2. __file__ 기준 (common/path_utils.py -> 프로젝트 루트)
    3. 현재 작업 디렉토리 (cwd)
    4. /app (Railway/Docker 환경)
    
    Returns:
        Path: 프로젝트 루트 경로
    """
    global _project_root
    
    if _project_root is not None:
        return _project_root
    
    # 1. 환경 변수 확인
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        _project_root = Path(env_root).resolve()
        logger.info(f"프로젝트 루트 (환경 변수): {_project_root}")
        return _project_root
    
    # 2. __file__ 기준 계산 (common/path_utils.py -> 프로젝트 루트)
    try:
        current_file = Path(__file__).resolve()
        # common/path_utils.py -> common -> 프로젝트 루트
        calculated_root = current_file.parent.parent
        if (calculated_root / "web").exists() and (calculated_root / "data").exists():
            _project_root = calculated_root
            logger.info(f"프로젝트 루트 (__file__ 기준): {_project_root}")
            return _project_root
    except Exception as e:
        logger.warning(f"__file__ 기준 경로 계산 실패: {e}")
    
    # 3. 현재 작업 디렉토리 확인
    cwd = Path.cwd()
    if (cwd / "web").exists() and (cwd / "data").exists():
        _project_root = cwd
        logger.info(f"프로젝트 루트 (cwd): {_project_root}")
        return _project_root
    
    # 4. /app (Railway/Docker 환경)
    app_path = Path("/app")
    if app_path.exists() and (app_path / "web").exists():
        _project_root = app_path
        logger.info(f"프로젝트 루트 (/app): {_project_root}")
        return _project_root
    
    # 5. fallback: 현재 파일의 부모의 부모
    _project_root = current_file.parent.parent
    logger.warning(f"프로젝트 루트를 확실히 찾지 못해 fallback 사용: {_project_root}")
    return _project_root


def get_data_dir() -> Path:
    """
    데이터 디렉토리 경로 반환
    
    Returns:
        Path: data 디렉토리 경로
    """
    global _data_dir
    
    if _data_dir is not None:
        return _data_dir
    
    project_root = get_project_root()
    _data_dir = project_root / "data"
    
    return _data_dir


def find_data_file(filename: str, required: bool = False) -> Optional[Path]:
    """
    데이터 파일을 찾아서 경로 반환
    
    Args:
        filename: 찾을 파일명 (예: "master_topics.json")
        required: 필수 파일인지 여부 (True면 없으면 예외 발생)
    
    Returns:
        Path: 파일 경로, 없으면 None (required=False인 경우)
    
    Raises:
        FileNotFoundError: required=True이고 파일을 찾을 수 없는 경우
    """
    data_dir = get_data_dir()
    file_path = data_dir / filename
    
    if file_path.exists():
        return file_path
    
    # 프로젝트 루트에서도 찾기 (하위 호환성)
    project_root = get_project_root()
    root_file_path = project_root / filename
    if root_file_path.exists():
        logger.warning(f"파일이 data 폴더가 아닌 루트에 있습니다: {root_file_path}")
        return root_file_path
    
    if required:
        raise FileNotFoundError(
            f"필수 데이터 파일을 찾을 수 없습니다: {filename}\n"
            f"검색 경로:\n"
            f"  - {file_path}\n"
            f"  - {root_file_path}\n"
            f"프로젝트 루트: {project_root}\n"
            f"데이터 디렉토리: {data_dir}"
        )
    
    return None


def list_data_files(pattern: str = "*") -> List[Path]:
    """
    데이터 디렉토리의 파일 목록 반환
    
    Args:
        pattern: 파일 패턴 (예: "*.json", "master_*.json")
    
    Returns:
        List[Path]: 파일 경로 리스트
    """
    data_dir = get_data_dir()
    
    if not data_dir.exists():
        logger.warning(f"데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        return []
    
    try:
        files = list(data_dir.glob(pattern))
        return sorted(files)
    except Exception as e:
        logger.error(f"데이터 파일 목록 조회 실패: {e}")
        return []


def reset_cache():
    """캐시 초기화 (테스트용)"""
    global _project_root, _data_dir
    _project_root = None
    _data_dir = None
