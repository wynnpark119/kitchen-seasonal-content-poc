"""
파일 로더 유틸리티 모듈

JSON, CSV 등 데이터 파일을 안정적으로 로드하는 유틸리티
에러 처리 및 로깅 통합
"""
import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import pandas as pd

from common.path_utils import find_data_file, get_data_dir

logger = logging.getLogger(__name__)


def load_json(
    filename: str,
    required: bool = False,
    fallback_path: Optional[Union[str, Path]] = None
) -> Optional[Dict[str, Any]]:
    """
    JSON 파일을 로드
    
    Args:
        filename: 파일명 (예: "master_topics.json")
        required: 필수 파일인지 여부
        fallback_path: 대체 경로 (filename을 찾지 못한 경우 시도)
    
    Returns:
        Dict: JSON 데이터, 실패 시 None (required=False인 경우)
    
    Raises:
        FileNotFoundError: required=True이고 파일을 찾을 수 없는 경우
        json.JSONDecodeError: JSON 파싱 실패 시
    """
    # 1. 데이터 디렉토리에서 찾기
    file_path = find_data_file(filename, required=False)
    
    # 2. fallback_path 시도
    if file_path is None and fallback_path:
        fallback_path_obj = Path(fallback_path)
        if fallback_path_obj.exists():
            file_path = fallback_path_obj
            logger.info(f"Fallback 경로에서 파일 발견: {file_path}")
    
    # 3. required=True인데 파일이 없으면 예외 발생
    if file_path is None:
        if required:
            raise FileNotFoundError(
                f"필수 JSON 파일을 찾을 수 없습니다: {filename}\n"
                f"데이터 디렉토리: {get_data_dir()}"
            )
        logger.warning(f"JSON 파일을 찾을 수 없습니다: {filename}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"JSON 파일 로드 성공: {file_path}")
        return data
    except json.JSONDecodeError as e:
        error_msg = f"JSON 파싱 오류 ({file_path}): {e}"
        logger.error(error_msg)
        if required:
            raise json.JSONDecodeError(error_msg, e.doc, e.pos)
        return None
    except Exception as e:
        error_msg = f"JSON 파일 로드 실패 ({file_path}): {e}"
        logger.error(error_msg, exc_info=True)
        if required:
            raise
        return None


def load_csv(
    filename: str,
    required: bool = False,
    **pd_read_csv_kwargs
) -> Optional[pd.DataFrame]:
    """
    CSV 파일을 pandas DataFrame으로 로드
    
    Args:
        filename: 파일명 (예: "data.csv")
        required: 필수 파일인지 여부
        **pd_read_csv_kwargs: pandas.read_csv()에 전달할 추가 인자
    
    Returns:
        pd.DataFrame: CSV 데이터, 실패 시 None (required=False인 경우)
    
    Raises:
        FileNotFoundError: required=True이고 파일을 찾을 수 없는 경우
    """
    file_path = find_data_file(filename, required=False)
    
    if file_path is None:
        if required:
            raise FileNotFoundError(
                f"필수 CSV 파일을 찾을 수 없습니다: {filename}\n"
                f"데이터 디렉토리: {get_data_dir()}"
            )
        logger.warning(f"CSV 파일을 찾을 수 없습니다: {filename}")
        return None
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8', **pd_read_csv_kwargs)
        logger.info(f"CSV 파일 로드 성공: {file_path} (행 수: {len(df)})")
        return df
    except Exception as e:
        error_msg = f"CSV 파일 로드 실패 ({file_path}): {e}"
        logger.error(error_msg, exc_info=True)
        if required:
            raise
        return None


def save_json(
    data: Dict[str, Any],
    filename: str,
    create_dir: bool = True
) -> Path:
    """
    JSON 파일로 저장
    
    Args:
        data: 저장할 데이터
        filename: 파일명
        create_dir: 디렉토리가 없으면 생성할지 여부
    
    Returns:
        Path: 저장된 파일 경로
    """
    data_dir = get_data_dir()
    
    if create_dir:
        data_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = data_dir / filename
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 파일 저장 성공: {file_path}")
        return file_path
    except Exception as e:
        error_msg = f"JSON 파일 저장 실패 ({file_path}): {e}"
        logger.error(error_msg, exc_info=True)
        raise


def check_file_exists(filename: str) -> tuple[bool, Optional[Path]]:
    """
    파일 존재 여부 확인
    
    Args:
        filename: 파일명
    
    Returns:
        tuple[bool, Optional[Path]]: (존재 여부, 파일 경로)
    """
    file_path = find_data_file(filename, required=False)
    exists = file_path is not None and file_path.exists()
    return exists, file_path
