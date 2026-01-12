#!/bin/bash
# Railway CLI를 사용하여 마이그레이션 실행

set -e

echo "🚀 Railway 마이그레이션 실행"
echo ""

# Railway 프로젝트 연결 확인
if ! railway status &>/dev/null; then
    echo "⚠️  Railway 프로젝트가 연결되지 않았습니다."
    echo "다음 명령어로 연결하세요:"
    echo "  railway link"
    exit 1
fi

echo "✅ Railway 프로젝트 연결됨"
echo ""

# PostgreSQL 서비스 선택
echo "📦 PostgreSQL 서비스에 연결 중..."
railway service postgres-tezk 2>/dev/null || railway service

# DATABASE_URL 환경 변수 설정 (Railway CLI가 자동으로 주입)
echo ""
echo "🔧 DATABASE_URL 환경 변수 설정 중..."
export DATABASE_URL=$(railway variables --service postgres-tezk 2>/dev/null | grep DATABASE_URL | awk '{print $3}' || echo "")

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL을 찾을 수 없습니다."
    echo "Railway 대시보드에서 공개 DATABASE_URL을 확인하세요."
    exit 1
fi

echo "✅ DATABASE_URL 설정됨"
echo ""

# 마이그레이션 실행
echo "📝 마이그레이션 실행 중..."
cd "$(dirname "$0")/.."
python3 migrations/run_migration.py

echo ""
echo "✅ 마이그레이션 완료!"
