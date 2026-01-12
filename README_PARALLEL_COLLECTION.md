# 병렬 Reddit 수집 가이드

MCP를 통한 병렬 실행이 제한적이므로, Apify Client SDK를 직접 사용하여 병렬 수집을 수행합니다.

## 방법 1: Node.js 사용

### 설치
```bash
npm install apify-client
```

### 실행
```bash
node collect_parallel_apify_client.js
```

## 방법 2: Python 사용 (권장)

### 설치
```bash
pip install apify-client
```

### 실행
```bash
python collect_parallel_apify_client.py
```

## 사용하는 Actor

- **Actor**: `fatihtahta/reddit-scraper-search-fast`
- 빠른 수집 속도와 효율적인 병렬 처리에 최적화됨

## 주요 차이점

### MCP 방식의 한계
- MCP는 순차적으로 실행되거나 병렬 실행이 제한적
- 여러 키워드를 동시에 시작하기 어려움

### Apify Client SDK 방식의 장점
- 모든 키워드를 동시에 시작 가능
- 각 키워드가 독립적으로 실행됨
- Apify 플랫폼에서 병렬 처리됨
- `fatihtahta/reddit-scraper-search-fast` 액터로 빠른 수집 가능

## 수집 조건

- **각 키워드당 포스트**: 200개
- **댓글**: 포스트당 2개씩 (인기순)
- **정렬**: hot (인기순)
- **검색 기간**: all (전체 기간)
- **NSFW 제외**: True
- **Proxy**: Apify Residential Proxy

## 키워드 목록 (총 20개)

### SPRING_RECIPES (5개)
1. spring dinner ideas
2. easy spring meals
3. what to cook in spring
4. spring meal prep
5. light spring recipes

### SPRING_KITCHEN_STYLING (5개)
1. spring kitchen decor
2. kitchen spring refresh
3. spring table setting ideas
4. how to decorate kitchen for spring
5. spring kitchen ideas

### REFRIGERATOR_ORGANIZATION (5개)
1. refrigerator organization
2. fridge organization tips
3. how to organize refrigerator
4. refrigerator storage ideas
5. fridge organization system

### VEGETABLE_PREP_HANDLING (5개)
1. vegetable prep
2. how to prep vegetables
3. vegetable storage tips
4. how to store vegetables
5. vegetable washing tips

## 실행 결과

실행 후 `collection_results.json` 파일에 다음 정보가 저장됩니다:
- 각 키워드의 Run ID
- Dataset ID
- 실행 상태
- 사용 비용

## 참고사항

- 모든 Run이 동시에 시작되지만, 완료 시간은 키워드마다 다를 수 있습니다
- Apify 콘솔(https://console.apify.com)에서 진행 상황을 실시간으로 확인할 수 있습니다
- 각 Run의 완료 상태는 `get_actor_run()` API를 사용하여 확인할 수 있습니다
