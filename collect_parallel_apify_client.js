/**
 * Apify Client SDK를 사용한 병렬 Reddit 수집
 * MCP 대신 직접 Apify API를 호출하여 병렬 실행
 * 
 * 실행 방법:
 *   npm install apify-client
 *   node collect_parallel_apify_client.js
 */

const { ApifyClient } = require('apify-client');

// API 토큰으로 클라이언트 초기화
const client = new ApifyClient({
    token: process.env.APIFY_API_TOKEN || 'your-apify-api-token-here',
});

// 20개 키워드 정의 (카테고리별 5개씩)
const keywords = {
    SPRING_RECIPES: [
        "spring dinner ideas",
        "easy spring meals",
        "what to cook in spring",
        "spring meal prep",
        "light spring recipes"
    ],
    SPRING_KITCHEN_STYLING: [
        "spring kitchen decor",
        "kitchen spring refresh",
        "spring table setting ideas",
        "how to decorate kitchen for spring",
        "spring kitchen ideas"
    ],
    REFRIGERATOR_ORGANIZATION: [
        "refrigerator organization",
        "fridge organization tips",
        "how to organize refrigerator",
        "refrigerator storage ideas",
        "fridge organization system"
    ],
    VEGETABLE_PREP_HANDLING: [
        "vegetable prep",
        "how to prep vegetables",
        "vegetable storage tips",
        "how to store vegetables",
        "vegetable washing tips"
    ]
};

// 모든 키워드를 flat하게
const allKeywords = Object.values(keywords).flat();

console.log(`총 ${allKeywords.length}개 키워드 수집 시작`);
console.log('='.repeat(60));

// 병렬 실행 함수
async function runAllScrapers() {
    const runs = [];
    const runInfo = [];
    
    // 각 키워드에 대해 Actor 실행 시작
    for (const keyword of allKeywords) {
        try {
            // fatihtahta/reddit-scraper-search-fast 사용
            const run = client.actor('fatihtahta/reddit-scraper-search-fast').call({
                queries: [keyword],
                sort: 'hot',  // 또는 'top'
                timeframe: 'all',
                maxPosts: 200,
                maxComments: 2,
                scrapeComments: true,
                includeNsfw: false
            });
            
            runs.push(run);
            runInfo.push({ keyword, run });
            console.log(`✅ 시작: ${keyword} (Run ID: ${run.id})`);
        } catch (error) {
            console.error(`❌ 오류 (${keyword}):`, error.message);
        }
    }
    
    console.log(`\n총 ${runs.length}개 실행 시작됨`);
    console.log('='.repeat(60));
    
    // 모든 실행이 완료될 때까지 대기
    console.log('\n수집 진행 중... (완료될 때까지 대기)');
    const results = await Promise.all(runs);
    
    console.log('\n' + '='.repeat(60));
    console.log('✅ 모든 수집 완료!');
    console.log('='.repeat(60));
    
    return { results, runInfo };
}

// 실행
runAllScrapers()
    .then(({ results, runInfo }) => {
        console.log(`\n완료된 작업: ${results.length}개\n`);
        
        // 각 결과의 dataset ID 및 상태 출력
        results.forEach((result, index) => {
            const info = runInfo[index];
            console.log(`${index + 1}. ${info.keyword}`);
            console.log(`   Run ID: ${result.id}`);
            console.log(`   Status: ${result.status}`);
            console.log(`   Dataset ID: ${result.defaultDatasetId}`);
            console.log(`   Usage: $${result.usageTotalUsd || 0}`);
            console.log('');
        });
        
        // 결과를 JSON 파일로 저장
        const fs = require('fs');
        const output = {
            completedAt: new Date().toISOString(),
            totalKeywords: results.length,
            results: results.map((result, index) => ({
                keyword: runInfo[index].keyword,
                runId: result.id,
                status: result.status,
                datasetId: result.defaultDatasetId,
                usageUsd: result.usageTotalUsd || 0
            }))
        };
        
        fs.writeFileSync(
            'collection_results.json',
            JSON.stringify(output, null, 2)
        );
        
        console.log('결과가 collection_results.json에 저장되었습니다.');
    })
    .catch(error => {
        console.error('❌ 오류 발생:', error);
        process.exit(1);
    });
