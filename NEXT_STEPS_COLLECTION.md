# Reddit 데이터 수집 다음 단계

## 현재 상황

### ✅ 수집 완료 (2개 키워드)
1. **spring dinner ideas**
   - Dataset ID: `Yu6o5q1FKWhb4jdcH`
   - Total Items: 889개
   - Status: 수집 완료, DB 저장 필요

2. **easy spring meals**
   - Dataset ID: `BdiwpZTKHdd7SATso`
   - Total Items: 830개
   - Status: 수집 완료, DB 저장 필요

### ⏳ 남은 키워드 (98개)
- SPRING_RECIPES: 8개 남음
- SPRING_KITCHEN_STYLING: 26개
- REFRIGERATOR_ORGANIZATION: 26개
- VEGETABLE_PREP_HANDLING: 26개

## 문제 상황
- MCP 세션 오류 발생 (Session ID not found)
- Apify Actor 호출 불가 상태

## 해결 방법

### 1. 수집 완료된 데이터 저장
MCP 세션이 복구되면 다음 순서로 진행:

```python
# 1. 데이터 가져오기
items_1 = mcp_apify_get_actor_output("Yu6o5q1FKWhb4jdcH", limit=889, offset=0)
items_2 = mcp_apify_get_actor_output("BdiwpZTKHdd7SATso", limit=830, offset=0)

# 2. 데이터베이스에 저장
from worker.pipeline.db import create_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results

run_id = create_pipeline_run("collect", "running")
process_apify_results(items_1, "spring dinner ideas", run_id)
process_apify_results(items_2, "easy spring meals", run_id)
```

### 2. 나머지 키워드 수집
MCP 세션이 복구되면 각 키워드에 대해:

```python
mcp_apify_call_actor(
    actor="harshmaur/reddit-scraper",
    step="call",
    input={
        "searchTerms": ["키워드"],
        "maxPostsCount": 900,
        "maxCommentsPerPost": 3,
        "fastMode": True,
        "searchSort": "hot",
        "searchTime": "all",
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
    }
)
```

## 준비된 스크립트
- `save_collected_data_to_db.py`: 수집 완료된 데이터 저장
- `continue_collection.py`: 남은 키워드 목록 확인
- `COLLECTION_STATUS.md`: 전체 수집 현황

## 다음 작업
1. MCP 세션 복구 대기 또는 재연결
2. 수집 완료된 2개 키워드 데이터 저장
3. 나머지 98개 키워드 순차 수집
