#!/bin/bash
# Railway PostgreSQL 설정 및 마이그레이션 실행 스크립트

echo "=========================================="
echo "Railway PostgreSQL 설정 가이드"
echo "=========================================="
echo ""

echo "1단계: Railway 웹 대시보드에서 PostgreSQL 추가"
echo "  - https://railway.app 접속"
echo "  - 프로젝트 'kitchen-seasonal-content-poc' 선택"
echo "  - 'New' 버튼 클릭 → 'Database' → 'PostgreSQL' 선택"
echo "  - PostgreSQL 서비스가 생성되면 자동으로 DATABASE_URL이 설정됩니다"
echo ""

echo "2단계: DATABASE_URL 확인"
echo "  railway variables --service streamlit | grep DATABASE_URL"
echo ""

echo "3단계: 마이그레이션 실행"
echo "  DATABASE_URL이 설정되면 다음 명령어로 마이그레이션 실행:"
echo "  python migrations/run_migration.py"
echo ""

echo "=========================================="
echo "현재 상태 확인"
echo "=========================================="

# DATABASE_URL 확인
if railway variables --service streamlit 2>/dev/null | grep -q DATABASE_URL; then
    echo "✅ DATABASE_URL이 설정되어 있습니다!"
    DATABASE_URL=$(railway variables --service streamlit 2>/dev/null | grep DATABASE_URL | awk '{print $3}')
    echo "DATABASE_URL: ${DATABASE_URL:0:50}..."
    echo ""
    echo "마이그레이션을 실행하시겠습니까? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "마이그레이션 실행 중..."
        export DATABASE_URL
        python migrations/run_migration.py
    fi
else
    echo "❌ DATABASE_URL이 설정되지 않았습니다."
    echo ""
    echo "Railway 웹 대시보드에서 PostgreSQL 서비스를 추가하세요:"
    echo "1. https://railway.app 접속"
    echo "2. 프로젝트 선택"
    echo "3. 'New' → 'Database' → 'PostgreSQL'"
    echo ""
    echo "PostgreSQL 서비스 추가 후 이 스크립트를 다시 실행하세요."
fi
