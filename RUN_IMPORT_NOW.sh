#!/bin/bash
# JSON Import 실행 스크립트

cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 이전에 성공한 DATABASE_URL 설정
export DATABASE_URL="postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@crossover.proxy.rlwy.net:19207/railway"

echo "============================================================"
echo "JSON Import 실행"
echo "============================================================"
echo "DATABASE_URL: ...@crossover.proxy.rlwy.net:19207/railway"
echo ""

# 1단계: DB 연결 테스트
echo "[1/3] DB 연결 테스트..."
python3 scripts/db_smoke_test.py
if [ $? -ne 0 ]; then
    echo "❌ DB 연결 실패. DATABASE_URL을 확인하세요."
    exit 1
fi

echo ""
echo "[2/3] Import 검증 (Dry run)..."
python3 scripts/import_smoke_test.py \
    --input data/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --sample-size 10 \
    --dry-run

if [ $? -ne 0 ]; then
    echo "⚠️  검증 실패. 계속 진행할까요? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

echo ""
echo "[3/3] 실제 Import 실행..."
echo "단일 파일부터 시작합니다: spring_dinner_ideas_Chej96NJu2xomUrg1.json"
echo ""

python3 scripts/import_json_to_db.py \
    --input data/spring_dinner_ideas_Chej96NJu2xomUrg1.json \
    --batch-size 500 \
    --max-errors 1000 \
    --job-id import-$(date +%Y%m%d-%H%M%S)

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Import 성공!"
    echo ""
    echo "다음 파일들도 Import할까요? (y/n)"
    read -r response
    if [ "$response" == "y" ]; then
        echo ""
        echo "전체 디렉토리 Import 실행..."
        python3 scripts/import_json_to_db.py \
            --input data/ \
            --batch-size 500 \
            --max-errors 1000 \
            --job-id import-all-$(date +%Y%m%d-%H%M%S)
    fi
else
    echo ""
    echo "❌ Import 실패. 로그를 확인하세요."
    exit 1
fi

echo ""
echo "============================================================"
echo "완료!"
echo "============================================================"
