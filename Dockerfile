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

# Streamlit 설정 (이미 COPY . . 에서 복사됨)
RUN mkdir -p .streamlit

# 시작 스크립트 실행 권한 부여
RUN chmod +x start_streamlit.sh

# 포트 노출 (Railway는 동적으로 포트를 할당하므로 일반적인 포트 사용)
EXPOSE 8501

# Streamlit 실행 (Railway의 startCommand가 우선되지만, 기본값으로 설정)
CMD ["bash", "start_streamlit.sh"]
