# Reddit 데이터 수집 현황

## 수집 완료된 키워드 (2개)

### 1. spring dinner ideas
- **Dataset ID**: `Yu6o5q1FKWhb4jdcH`
- **Total Items**: 889개
- **Status**: 수집 완료, 데이터베이스 저장 필요

### 2. easy spring meals
- **Dataset ID**: `BdiwpZTKHdd7SATso`
- **Total Items**: 830개
- **Status**: 수집 완료, 데이터베이스 저장 필요

## 데이터베이스 저장 방법

수집 완료된 데이터를 데이터베이스에 저장하려면:

```python
from worker.pipeline.db import create_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from mcp_apify_get_actor_output import get_actor_output

# 1. 파이프라인 run 생성
run_id = create_pipeline_run("collect", "running")

# 2. 데이터 가져오기
items_1 = get_actor_output("Yu6o5q1FKWhb4jdcH", limit=889, offset=0)
items_2 = get_actor_output("BdiwpZTKHdd7SATso", limit=830, offset=0)

# 3. 데이터베이스에 저장
process_apify_results(items_1, "spring dinner ideas", run_id)
process_apify_results(items_2, "easy spring meals", run_id)
```

## 남은 키워드 수집 (86개)

### SPRING_RECIPES 카테고리 (8개 남음)
- what to cook in spring
- spring meal prep
- light spring recipes
- quick spring dinner
- spring weeknight meals
- healthy spring meals
- what do you cook in spring
- best spring dinner ideas

### SPRING_KITCHEN_STYLING 카테고리 (26개)
- spring kitchen decor
- kitchen spring refresh
- spring table setting ideas
- how to decorate kitchen for spring
- spring kitchen ideas
- kitchen spring makeover
- spring kitchen styling
- spring home decor kitchen
- spring kitchen update
- spring kitchen refresh ideas
- spring kitchen decoration
- spring kitchen design ideas
- spring kitchen colors
- spring kitchen accessories
- spring kitchen centerpiece
- spring kitchen window decor
- spring kitchen counter decor
- spring kitchen wall decor
- spring kitchen lighting
- spring kitchen plants
- spring kitchen organization decor
- spring kitchen rug
- spring kitchen curtains
- spring kitchen art
- how do you decorate your kitchen for spring
- what spring decor do you use in kitchen
- anyone else refresh kitchen for spring
- best way to style kitchen for spring
- what spring colors work in kitchen
- how do you make kitchen feel spring

### REFRIGERATOR_ORGANIZATION 카테고리 (26개)
- refrigerator organization
- fridge organization tips
- how to organize refrigerator
- refrigerator storage ideas
- fridge organization system
- refrigerator organization hacks
- how do you organize your fridge
- fridge organization methods
- refrigerator organization tips
- fridge storage organization
- refrigerator organization ideas
- best way to organize fridge
- refrigerator drawer organization
- fridge shelf organization
- refrigerator door organization
- fridge organization containers
- refrigerator organization bins
- fridge organization labels
- refrigerator organization system
- fridge organization routine
- refrigerator organization before after
- fridge organization meal prep
- refrigerator organization small fridge
- fridge organization family
- how do you organize your refrigerator
- what's the best way to organize fridge
- anyone else struggle with fridge organization
- how do you keep fridge organized
- what do you use to organize fridge
- best tips for refrigerator organization

### VEGETABLE_PREP_HANDLING 카테고리 (26개)
- vegetable prep
- how to prep vegetables
- vegetable storage tips
- how to store vegetables
- vegetable washing tips
- how to wash vegetables
- vegetable prep meal prep
- best way to prep vegetables
- vegetable handling tips
- how to clean vegetables
- vegetable prep ideas
- vegetable storage methods
- vegetable prep containers
- vegetable storage containers
- how to store cut vegetables
- vegetable prep ahead
- vegetable washing methods
- vegetable prep for meal prep
- vegetable storage fridge
- vegetable prep routine
- vegetable washing techniques
- vegetable prep tips
- vegetable storage hacks
- vegetable prep organization
- how do you prep vegetables
- what's the best way to prep vegetables
- how do you wash vegetables
- anyone else prep vegetables ahead
- how do you store vegetables
- best way to store cut vegetables

## Actor 호출 설정

각 키워드에 대해 다음 설정으로 Actor 호출:

```json
{
  "searchTerms": ["키워드"],
  "searchPosts": true,
  "searchComments": false,
  "crawlCommentsPerPost": true,
  "maxPostsCount": 900,
  "maxCommentsPerPost": 3,
  "fastMode": true,
  "searchSort": "hot",
  "searchTime": "all",
  "includeNSFW": false,
  "proxy": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"]
  }
}
```

## 다음 단계

1. ✅ 수집 완료된 2개 키워드 데이터를 데이터베이스에 저장
2. ⏳ 나머지 86개 키워드에 대해 순차적으로 Actor 호출하여 수집
3. ⏳ 수집된 모든 데이터를 데이터베이스에 저장
