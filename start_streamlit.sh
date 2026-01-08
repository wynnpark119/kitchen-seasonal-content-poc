#!/bin/bash
# Railway용 Streamlit 시작 스크립트

# PORT 환경 변수가 없으면 기본값 8501 사용
PORT=${PORT:-8501}

# Streamlit 실행
streamlit run web/app.py \
  --server.address=0.0.0.0 \
  --server.port=$PORT \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false
