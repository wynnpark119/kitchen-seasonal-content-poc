# 배포 및 검증 체크리스트

## 배포 전 확인

- [ ] 코드 변경사항 커밋
- [ ] Railway Worker 서비스 Variables 확인:
  - [ ] `DATABASE_URL` 설정됨
  - [ ] `APIFY_API_TOKEN` 설정됨
  - [ ] `WORKER_MODE=save_keywords` 설정됨
  - [ ] `WORKER_ONCE=true` 설정됨

## 배포

```bash
git add .
git commit -m "Fix: Add connection pooling and batch processing for Apify data loading"
git push
```

Railway가 자동으로 재배포합니다.

## 배포 후 확인

### 1. Worker 로그 확인 (즉시)

Railway Worker 서비스 → **Logs** 탭:

**정상 시작:**
```
Connection pool created successfully
✅ Apify 클라이언트 초기화 완료
✅ 데이터베이스 연결 성공
총 20개 키워드 데이터 저장 시작
```

**배치 처리 확인:**
```
Processing 200 items...
Batch upserted 150 posts, 0 errors
```

**완료 확인:**
```
저장 완료!
  처리된 키워드: 20/20
  총 포스트: XXXX
  총 댓글: XXXX
```

### 2. 에러 로그 확인

다음 에러가 보이면 문제:
- ❌ "too many connections" → Connection pool 문제 (해결됨)
- ❌ "null value in column" → 데이터 검증 문제 (해결됨)
- ❌ "DATABASE_URL not found" → 환경 변수 문제

### 3. PostgreSQL Metrics 확인

Railway PostgreSQL 서비스 → **Metrics** 탭:
- 활성 연결 수 < 10 (정상)
- 활성 연결 수 > 50 (문제)

### 4. 데이터베이스 직접 확인

Railway PostgreSQL 서비스 → **Data** 탭:

```sql
-- 총 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY count DESC;

-- 최근 적재된 데이터
SELECT keyword, title, created_at 
FROM raw_reddit_posts 
ORDER BY created_at DESC 
LIMIT 10;
```

**예상 결과:**
- 총 포스트: 약 2000-4000개
- 키워드별: 각 키워드당 약 100-200개
- 최근 데이터: 방금 적재된 타임스탬프

### 5. Streamlit 대시보드 확인

Streamlit 서비스 URL 접속:
- **Raw Data Explorer** 탭 → **Reddit Posts**
- 데이터가 표시되는지 확인

---

## 문제 발생 시

### Connection Pool 에러

**증상**: "connection pool exhausted"
**해결**: 이미 수정됨 (connection pooling 적용)

### 데이터 검증 에러

**증상**: "null value in column"
**해결**: 이미 수정됨 (데이터 검증 강화)

### DATABASE_URL 에러

**증상**: "DATABASE_URL not found"
**해결**: 
1. Railway Worker 서비스 Variables 확인
2. PostgreSQL 서비스의 DATABASE_URL 복사
3. Worker 서비스 Variables에 추가

---

## 성능 비교

### 이전
- 연결 생성: 4,000번
- 예상 시간: 5-10분

### 이후
- 연결 생성: 약 40번
- 예상 시간: 1-2분

**약 5배 빠름**
