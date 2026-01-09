"""
설정 관리 모듈
환경 변수 로드 및 설정 제공
"""
import os
from pathlib import Path

# .env 파일 로드 (dotenv가 없어도 동작하도록 fallback 제공)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
except ImportError:
    # dotenv가 없으면 .env 파일을 직접 읽기
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # 이미 환경 변수가 설정되어 있지 않을 때만 설정
                    if key and not os.getenv(key):
                        os.environ[key] = value

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
