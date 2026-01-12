#!/bin/bash
# Apify REST API를 직접 호출하여 병렬 수집 시작

APIFY_TOKEN="${APIFY_API_TOKEN:-your-apify-api-token-here}"
ACTOR_ID="fatihtahta/reddit-scraper-search-fast"

echo "============================================================"
echo "Apify REST API로 병렬 Reddit 수집 시작"
echo "============================================================"
echo ""

# 키워드 배열
keywords=(
    "spring dinner ideas"
    "easy spring meals"
    "what to cook in spring"
    "spring meal prep"
    "light spring recipes"
    "spring kitchen decor"
    "kitchen spring refresh"
    "spring table setting ideas"
    "how to decorate kitchen for spring"
    "spring kitchen ideas"
    "refrigerator organization"
    "fridge organization tips"
    "how to organize refrigerator"
    "refrigerator storage ideas"
    "fridge organization system"
    "vegetable prep"
    "how to prep vegetables"
    "vegetable storage tips"
    "how to store vegetables"
    "vegetable washing tips"
)

echo "총 ${#keywords[@]}개 키워드 수집 시작"
echo ""

# 결과 저장용
results_file="collection_runs_started.json"
echo "[" > "$results_file"

for i in "${!keywords[@]}"; do
    keyword="${keywords[$i]}"
    echo "시작: $keyword"
    
    # Apify REST API 호출
    response=$(curl -s -X POST \
        "https://api.apify.com/v2/acts/${ACTOR_ID}/runs" \
        -H "Authorization: Bearer ${APIFY_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"queries\": [\"${keyword}\"],
            \"sort\": \"hot\",
            \"timeframe\": \"all\",
            \"maxPosts\": 200,
            \"maxComments\": 2,
            \"scrapeComments\": true,
            \"includeNsfw\": false
        }")
    
    # Run ID 추출
    run_id=$(echo "$response" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    
    if [ -n "$run_id" ]; then
        echo "  ✅ Run ID: $run_id"
        echo "  📊 콘솔: https://console.apify.com/view/runs/${run_id}"
        
        # JSON 결과 추가
        if [ $i -gt 0 ]; then
            echo "," >> "$results_file"
        fi
        echo "  {" >> "$results_file"
        echo "    \"keyword\": \"${keyword}\"," >> "$results_file"
        echo "    \"runId\": \"${run_id}\"," >> "$results_file"
        echo "    \"consoleUrl\": \"https://console.apify.com/view/runs/${run_id}\"" >> "$results_file"
        echo -n "  }" >> "$results_file"
    else
        echo "  ❌ 오류: $response"
    fi
    echo ""
done

echo "]" >> "$results_file"

echo "============================================================"
echo "✅ 모든 Run 시작 완료!"
echo "============================================================"
echo ""
echo "결과가 ${results_file}에 저장되었습니다."
echo ""
echo "Apify 콘솔에서 진행 상황 확인:"
echo "https://console.apify.com"
