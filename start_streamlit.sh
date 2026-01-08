#!/bin/bash
# Railway용 Streamlit 시작 스크립트

# PORT 환경 변수가 없으면 기본값 8501 사용
PORT=${PORT:-8501}

# 디버깅: 환경 변수 출력
echo "Starting Streamlit..."
echo "PORT=$PORT"
echo "DATABASE_URL=${DATABASE_URL:0:50}..." # 처음 50자만 출력

# Streamlit 실행 (에러 발생 시에도 계속 실행되도록)
exec streamlit run web/app.py \
  --server.address=0.0.0.0 \
  --server.port=$PORT \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.runOnSave=false
