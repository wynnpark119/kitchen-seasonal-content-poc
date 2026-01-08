# Streamlit 대시보드용 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드 복사
COPY . .

# Streamlit 설정
RUN mkdir -p .streamlit
COPY .streamlit/config.toml .streamlit/config.toml 2>/dev/null || true

# 포트 노출
EXPOSE 8501

# Streamlit 실행
CMD ["streamlit", "run", "web/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
