#!/bin/bash
# Railway에서 병렬 Reddit 수집 실행 스크립트

echo "=========================================="
echo "Railway 병렬 Reddit 수집 실행"
echo "=========================================="
echo ""

# Railway CLI 설치 확인
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI가 설치되어 있지 않습니다."
    echo "설치: npm install -g @railway/cli"
    exit 1
fi

echo "✅ Railway CLI 확인됨"
echo ""

# 프로젝트 디렉토리 확인
if [ ! -f "run_parallel_collection.py" ]; then
    echo "❌ run_parallel_collection.py 파일을 찾을 수 없습니다."
    echo "프로젝트 루트 디렉토리에서 실행하세요."
    exit 1
fi

echo "✅ 스크립트 파일 확인됨"
echo ""

# 환경 변수 확인
echo "환경 변수 확인 중..."
railway variables

echo ""
echo "=========================================="
echo "실행 시작..."
echo "=========================================="
echo ""

# 실행
railway run python run_parallel_collection.py

echo ""
echo "=========================================="
echo "실행 완료!"
echo "=========================================="
echo ""
echo "Railway 콘솔에서 로그를 확인하세요:"
echo "https://railway.app"
echo ""
echo "Apify 콘솔에서 Run 상태 확인:"
echo "https://console.apify.com"
