# Apify 데이터 적재 완료 확인

## 확인 방법

### 1. Railway Worker 로그 확인 (가장 정확함)

Railway 대시보드 → **Worker 서비스** → **Logs** 탭에서 확인:

#### ✅ 완료된 경우:
```
============================================================
저장 완료!
  처리된 키워드: 20/20
  총 포스트: XXXX
  총 댓글: XXXX
============================================================

Pipeline run completed successfully: run_id=X
WORKER_ONCE=true로 설정되어 종료합니다.
```

#### ⏳ 아직 진행 중인 경우:
```
[1/20] Processing: spring dinner ideas
  Dataset ID: Chej96NJu2xomUrg1
  Dataset has 200 items
  Fetched 200 items (total: 200)
  Processing 200 items...
  ✅ spring dinner ideas: 150 posts, 300 comments

[2/20] Processing: easy spring meals
  ...
```

#### ❌ 실패한 경우:
```
❌ Error processing {keyword}: ...
❌ Fatal error processing {keyword}: ...
```

### 2. 데이터베이스 직접 확인

Railway PostgreSQL 서비스 → **Data** 탭에서 실행:

```sql
-- 총 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수 (20개 키워드 모두 확인)
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY keyword;

-- 최근 적재된 데이터 확인
SELECT keyword, title, created_at 
FROM raw_reddit_posts 
ORDER BY created_at DESC 
LIMIT 10;
```

**예상 결과 (완료된 경우):**
- 총 포스트: 약 2000-4000개
- 키워드별: 각 키워드당 약 100-200개
- 최근 데이터: 방금 적재된 타임스탬프

### 3. Pipeline Runs 확인

```sql
-- 최근 collect/save_keywords 실행 확인
SELECT run_id, run_type, status, started_at, completed_at, metadata
FROM pipeline_runs 
WHERE run_type IN ('collect', 'save_keywords')
ORDER BY started_at DESC 
LIMIT 1;
```

**완료된 경우:**
- `status`: `completed`
- `completed_at`: NULL이 아님
- `metadata`: `{"keywords_processed": 20, "total_posts": XXXX, ...}`

## 완료 기준

### ✅ 완료된 경우

1. **Worker 로그:**
   - "저장 완료!" 메시지
   - "처리된 키워드: 20/20"
   - "WORKER_ONCE=true로 설정되어 종료합니다."

2. **데이터베이스:**
   - 총 포스트 수 > 0
   - 15개 이상의 키워드에 데이터 있음
   - 최근 적재된 데이터의 타임스탬프가 최근

3. **Pipeline Run:**
   - `status` = `completed`
   - `completed_at`이 설정됨

### ⏳ 아직 진행 중인 경우

- Worker 로그에 키워드 처리 진행 상황이 보임
- "[X/20] Processing: ..." 메시지가 계속 나타남
- "저장 완료!" 메시지가 아직 없음

### ❌ 실패한 경우

- Worker 로그에 에러 메시지
- 데이터베이스에 데이터가 없거나 일부만 있음
- Pipeline Run의 `status` = `failed`

## 예상 소요 시간

- **키워드당**: 약 10-30초
- **전체 20개 키워드**: 약 5-10분

Worker가 시작된 시간을 기준으로 계산하면:
- 시작 후 5분 이내: 아직 진행 중일 가능성 높음
- 시작 후 10분 이상: 완료되었거나 문제가 있을 수 있음

## 문제 해결

### Worker가 아직 실행 중인 경우

- 로그에서 진행 상황 확인
- 완료될 때까지 대기

### Worker가 멈춘 경우

- 로그에서 마지막 메시지 확인
- 어느 키워드에서 멈췄는지 확인
- Worker 서비스 재시작

### 에러가 발생한 경우

- 로그에서 에러 메시지 확인
- `APIFY_API_TOKEN` 확인
- `DATABASE_URL` 확인
- Worker 서비스 재시작

## 빠른 확인

Railway Worker 서비스의 **Logs** 탭에서:

1. **마지막 메시지 확인**
   - "저장 완료!" → ✅ 완료
   - "[X/20] Processing" → ⏳ 진행 중
   - "Error" 또는 "❌" → ❌ 실패

2. **처리된 키워드 수 확인**
   - "처리된 키워드: 20/20" → ✅ 완료
   - "처리된 키워드: X/20" (X < 20) → ⏳ 진행 중 또는 ❌ 실패
