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

# data 디렉토리 생성
RUN mkdir -p data

# 마스터 토픽 JSON 파일 명시적으로 복사 (로컬 방식 유지)
COPY data/master_topics_final_kr_en_RICH_WHY.json data/

# 프로젝트 코드 복사
COPY . .

# 마스터 토픽 JSON 파일이 data 디렉토리에 있는지 확인
RUN if [ -f "data/master_topics_final_kr_en_RICH_WHY.json" ]; then \
        echo "✅ 마스터 토픽 JSON 파일 확인됨"; \
        ls -lh data/master_topics_final_kr_en_RICH_WHY.json; \
    else \
        echo "⚠️ 마스터 토픽 JSON 파일을 찾을 수 없습니다"; \
        find . -name "*master_topics*.json" -type f 2>/dev/null | head -5; \
    fi

# Streamlit 설정 (이미 COPY . . 에서 복사됨)
RUN mkdir -p .streamlit

# 시작 스크립트 실행 권한 부여
RUN chmod +x start_streamlit.sh

# 포트 노출 (Railway는 동적으로 포트를 할당하므로 일반적인 포트 사용)
EXPOSE 8501

# Streamlit 실행 (Railway의 startCommand가 우선되지만, 기본값으로 설정)
CMD ["bash", "start_streamlit.sh"]
