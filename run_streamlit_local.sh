#!/bin/bash
# 로컬에서 Streamlit 실행 스크립트

set -e

cd "$(dirname "$0")"

echo "🚀 Streamlit 로컬 실행"
echo ""

# DATABASE_URL 설정
export DATABASE_URL="postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway"

# 가상환경 확인 및 활성화 (있는 경우)
if [ -d ".venv" ]; then
    echo "✅ 가상환경 발견, 활성화 중..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "✅ 가상환경 발견, 활성화 중..."
    source venv/bin/activate
else
    echo "⚠️  가상환경이 없습니다. 시스템 Python을 사용합니다."
fi

# Streamlit 실행
echo ""
echo "📊 Streamlit 실행 중..."
echo "브라우저에서 http://localhost:8502 접속하세요"
echo ""
echo "중지하려면 Ctrl+C를 누르세요"
echo ""

streamlit run web/app.py --server.port 8502
