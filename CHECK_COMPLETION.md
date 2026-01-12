# 데이터 적재 완료 확인 가이드

## 빠른 확인 방법

### 방법 1: Railway Worker 로그 확인 (가장 빠름)

1. Railway 대시보드 → **Worker 서비스** → **Logs** 탭
2. 다음 메시지 확인:

```
============================================================
저장 완료!
  처리된 키워드: 20/20
  총 포스트: XXXX
  총 댓글: XXXX
============================================================
```

✅ **이 메시지가 보이면 → 적재 완료**

### 방법 2: 데이터베이스 직접 확인

Railway PostgreSQL 서비스 → **Data** 탭에서 실행:

```sql
-- 총 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수 (20개 키워드 모두 확인)
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY keyword;
```

**예상 결과:**
- 총 포스트: 약 2000-4000개 (키워드당 200개 × 20개)
- 키워드별: 각 키워드당 약 100-200개

✅ **포스트가 있으면 → 적재 완료**

### 방법 3: 확인 스크립트 실행

Railway Worker 서비스에서:

```bash
# Railway CLI 사용
railway run python verify_data_loaded.py

# 또는 Worker 서비스의 Variables에 임시로 추가:
# WORKER_MODE=verify_data
```

## 완료 기준

### ✅ 완료된 경우

- Worker 로그: "저장 완료! 처리된 키워드: 20/20"
- 데이터베이스: 총 포스트 수 > 0
- 키워드: 15개 이상의 키워드에 데이터 있음

### ❌ 아직 완료되지 않은 경우

- Worker 로그: 키워드 처리 진행 중
- 데이터베이스: 포스트 수 = 0
- 키워드: 일부 키워드만 데이터 있음

## 문제 해결

### Worker가 아직 실행 중인 경우

- Worker 로그에서 진행 상황 확인
- 완료될 때까지 대기 (보통 5-10분)

### Worker가 실패한 경우

- Worker 로그에서 에러 메시지 확인
- Variables에서 `APIFY_API_TOKEN` 확인
- Variables에서 `DATABASE_URL` 확인
- Worker 서비스 재시작

### 데이터가 일부만 적재된 경우

- Worker 로그에서 어느 키워드에서 실패했는지 확인
- 실패한 키워드만 다시 실행하거나 전체 재실행

## 확인 체크리스트

- [ ] Worker 로그: "저장 완료!" 메시지 확인
- [ ] 데이터베이스: 총 포스트 수 > 0 확인
- [ ] 키워드: 15개 이상 키워드에 데이터 확인
- [ ] 댓글: 총 댓글 수 확인 (선택사항)
