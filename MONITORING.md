# Railway Worker 실행 모니터링 가이드

## 로그 확인 방법

### Railway 대시보드에서 확인

1. **Railway 대시보드 접속**: https://railway.app/
2. 프로젝트 선택
3. **Worker 서비스** 클릭
4. **"Logs"** 탭 클릭
5. 실시간 로그 확인

## 정상 실행 시 예상 로그

### 1. 초기화 단계
```
Worker 시작
  모드: save_keywords
  간격: 3600초
  한 번만 실행: True
  Dry run: False
...
✅ Apify 클라이언트 초기화 완료
✅ 데이터베이스 연결 성공
Pipeline run 생성: run_id=1
```

### 2. 데이터 저장 진행
```
============================================================
총 20개 키워드 데이터 저장 시작
============================================================

[1/20] Processing: spring dinner ideas
  Dataset ID: Chej96NJu2xomUrg1
  Dataset has 200 items
  Fetched 200 items (total: 200)
  Processing 200 items...
  ✅ spring dinner ideas: 150 posts, 300 comments

[2/20] Processing: easy spring meals
  Dataset ID: hYNaDehMRGFbLd9sW
  ...
```

### 3. 완료 메시지
```
============================================================
저장 완료!
  처리된 키워드: 20/20
  총 포스트: XXXX
  총 댓글: XXXX
============================================================

Pipeline run completed successfully: run_id=1
WORKER_ONCE=true로 설정되어 종료합니다.
```

## 실행 시간 예상

- **키워드당**: 약 10-30초 (데이터셋 크기에 따라 다름)
- **전체 20개 키워드**: 약 5-10분

## 데이터베이스 확인 방법

### Streamlit 대시보드에서 확인

1. Streamlit 서비스 URL 접속
2. **"Raw Data Explorer"** 탭 클릭
3. **"Reddit Posts"** 선택
4. 키워드별로 데이터 확인

### SQL로 직접 확인

```sql
-- 총 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수 확인
SELECT keyword, COUNT(*) as post_count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY post_count DESC;

-- 총 댓글 수 확인
SELECT COUNT(*) FROM raw_reddit_comments;

-- 최근 수집된 데이터 확인
SELECT keyword, title, upvotes, created_at 
FROM raw_reddit_posts 
ORDER BY created_at DESC 
LIMIT 20;
```

## 문제 해결

### 로그에 에러가 보이는 경우

1. **APIFY_API_TOKEN 오류**
   - Worker 서비스 Variables에서 토큰 확인
   - Apify 콘솔에서 토큰 활성화 확인

2. **데이터베이스 연결 오류**
   - `DATABASE_URL` 변수 확인
   - PostgreSQL 서비스가 Online 상태인지 확인

3. **데이터셋을 찾을 수 없음**
   - Apify 콘솔에서 데이터셋 ID 확인
   - 데이터셋이 존재하는지 확인

### 실행이 멈춘 경우

1. **로그 확인**: 어느 키워드에서 멈췄는지 확인
2. **재시작**: Worker 서비스를 재시작하거나 재배포
3. **부분 완료 확인**: 이미 저장된 데이터는 그대로 유지됨

## 실행 완료 후

### Variables 복구

일회성 실행이 완료되면:

1. Worker 서비스의 **Variables** 탭으로 이동
2. 다음 변수 삭제 또는 변경:
   - `WORKER_MODE` 삭제 (또는 `collect`로 변경)
   - `WORKER_ONCE` 삭제 (또는 `false`로 변경)

이렇게 하면 Worker가 정상 모드로 동작합니다.

### 다음 단계

데이터 저장이 완료되면:
1. 데이터 분석 파이프라인 실행 (`WORKER_MODE=analyze`)
2. LLM 기반 brief 생성 (`WORKER_MODE=label`)
3. Streamlit 대시보드에서 결과 확인
