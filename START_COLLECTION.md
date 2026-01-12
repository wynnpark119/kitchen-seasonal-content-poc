# 🚀 빠른 실행 가이드

## 가장 빠른 방법: 직접 터미널에서 실행

로컬 터미널을 열고 다음 명령어를 실행하세요:

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
python3 run_local_quick.py
```

또는:

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
bash run_quick_curl.sh
```

## MCP를 통한 빠른 실행 (권장)

Cursor에서 MCP 도구를 사용하여 각 키워드를 개별적으로 빠르게 호출할 수 있습니다.

### 실행할 명령어 (20개)

각 키워드에 대해 다음 형식으로 MCP 호출:

```
mcp_apify_call-actor(
    actor='fatihtahta/reddit-scraper-search-fast',
    step='call',
    input={
        'queries': ['키워드'],
        'sort': 'hot',
        'timeframe': 'all',
        'maxPosts': 200,
        'maxComments': 2,
        'scrapeComments': True,
        'includeNsfw': False
    }
)
```

### 키워드 목록 (20개)

1. spring dinner ideas
2. easy spring meals
3. what to cook in spring
4. spring meal prep
5. light spring recipes
6. spring kitchen decor
7. kitchen spring refresh
8. spring table setting ideas
9. how to decorate kitchen for spring
10. spring kitchen ideas
11. refrigerator organization
12. fridge organization tips
13. how to organize refrigerator
14. refrigerator storage ideas
15. fridge organization system
16. vegetable prep
17. how to prep vegetables
18. vegetable storage tips
19. how to store vegetables
20. vegetable washing tips

## 가장 빠른 방법: MCP로 연속 호출

AI에게 "20개 키워드를 MCP로 빠르게 연속 호출해줘"라고 요청하면 됩니다.
