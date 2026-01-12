# Railway에서 병렬 Reddit 수집 실행 가이드

## 제일 좋은 방법: Railway Worker에서 실행

Railway Worker는 이미 설정되어 있고 네트워크 접근이 가능하므로, 여기서 병렬 수집을 실행하는 것이 가장 좋습니다.

## 설정 방법

### 1. Railway 환경 변수 설정

Railway 콘솔에서 Worker 서비스의 환경 변수에 다음을 추가:

```
APIFY_API_TOKEN=your-apify-api-token-here
DATABASE_URL=<기존 DATABASE_URL>
```

### 2. 실행 방법

#### 방법 A: Worker 서비스에서 직접 실행 (권장)

Railway Worker 서비스의 환경 변수에 다음을 추가:

```
WORKER_MODE=collect_parallel
WORKER_ONCE=true
```

또는 Railway CLI로 직접 실행:

```bash
railway run python run_parallel_collection.py
```

#### 방법 B: 기존 Worker 파이프라인에 통합

`worker/run_pipeline.py`에 `collect_parallel` 모드를 추가하여 기존 워크플로우에 통합할 수 있습니다.

## 스크립트 설명

### `run_parallel_collection.py`
- Railway Worker에서 실행할 메인 스크립트
- Apify Client SDK를 사용하여 20개 키워드를 병렬로 수집
- 데이터를 자동으로 데이터베이스에 저장

### `worker/pipeline/collect_reddit_parallel.py`
- 병렬 수집 로직을 담은 모듈
- 각 키워드에 대해 `fatihtahta/reddit-scraper-search-fast` 액터 실행
- 완료된 Run의 데이터를 자동으로 가져와서 DB에 저장

## 수집 조건

- **각 키워드당 포스트**: 200개
- **댓글**: 포스트당 2개씩 (인기순)
- **정렬**: hot (인기순)
- **검색 기간**: all (전체 기간)
- **NSFW 제외**: True

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

## 장점

1. **네트워크 접근**: Railway Worker는 네트워크 접근이 자유로움
2. **권한 문제 없음**: SSL 인증서 등 권한 문제 없음
3. **백그라운드 실행**: Worker 서비스에서 자동으로 실행
4. **자동 저장**: 수집된 데이터가 자동으로 DB에 저장됨
5. **로깅**: Railway 로그에서 진행 상황 확인 가능

## 모니터링

Railway 콘솔에서:
- Worker 서비스의 로그를 확인하여 진행 상황 모니터링
- Apify 콘솔에서 각 Run의 상태 확인 가능

## 참고사항

- 모든 Run이 동시에 시작되지만, 완료 시간은 키워드마다 다를 수 있습니다
- Apify 콘솔(https://console.apify.com)에서 진행 상황을 실시간으로 확인할 수 있습니다
- 각 Run의 완료를 기다려서 데이터를 자동으로 가져와 DB에 저장합니다
