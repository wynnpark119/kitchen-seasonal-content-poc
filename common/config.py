"""
설정 관리 모듈
환경 변수 로드 및 설정 제공
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Database 설정 (worker/pipeline/db.py와 동일한 순서로 읽기)
DATABASE_URL = (
    os.getenv("DATABASE_URL") or 
    os.getenv("RAILWAY_DATABASE_URL") or
    os.getenv("POSTGRES_URL") or
    os.getenv("POSTGRES_PRIVATE_URL")
)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "kitchen_seasonal_db")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# Application 설정
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", 8501))

# API Keys (추후 추가)
# REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
# REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
