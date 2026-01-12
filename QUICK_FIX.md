# 빠른 해결 가이드: Streamlit에서 데이터가 보이지 않을 때

## 즉시 확인할 사항

### 1. Worker 실행 완료 확인 (가장 중요!)

Railway Worker 서비스 → **Logs** 탭에서 확인:

✅ **완료된 경우:**
```
저장 완료!
  처리된 키워드: 20/20
  총 포스트: XXXX
  총 댓글: XXXX
```

❌ **아직 실행 중:**
- 키워드 처리 진행 상황이 보임
- "저장 완료!" 메시지가 아직 없음

### 2. 데이터베이스 직접 확인

Railway PostgreSQL 서비스 → **Data** 탭에서 실행:

```sql
-- 총 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY count DESC;
```

**결과:**
- 포스트가 0개면 → Worker가 아직 실행 중이거나 실패함
- 포스트가 있으면 → Streamlit 설정 문제

### 3. Streamlit 서비스 Variables 확인

Railway Streamlit 서비스 → **Variables** 탭:

- `DATABASE_URL`이 설정되어 있는지 확인
- 값이 Worker와 동일한 PostgreSQL 서비스의 URL인지 확인

### 4. Streamlit 서비스 재시작

데이터베이스에 데이터가 있는데 Streamlit에서 보이지 않으면:

1. Streamlit 서비스 → **Settings** 탭
2. **"Redeploy"** 클릭
3. 재배포 완료 후 대시보드 새로고침 (Ctrl+R 또는 Cmd+R)

## 단계별 해결

### Step 1: Worker 완료 확인
```
✅ Worker 로그에서 "저장 완료!" 확인
```

### Step 2: 데이터베이스 확인
```
✅ PostgreSQL Data 탭에서 포스트 수 확인
```

### Step 3: Streamlit Variables 확인
```
✅ DATABASE_URL 설정 확인
```

### Step 4: Streamlit 재시작
```
✅ Redeploy 후 새로고침
```

## 자주 발생하는 문제

### 문제: Worker가 아직 실행 중
**해결**: Worker 로그에서 완료될 때까지 대기

### 문제: 데이터베이스에 데이터 없음
**해결**: Worker 로그 확인, 에러가 있으면 수정 후 재실행

### 문제: Streamlit DATABASE_URL 미설정
**해결**: Streamlit 서비스 Variables에 DATABASE_URL 추가

### 문제: Streamlit이 다른 DB에 연결
**해결**: Worker와 동일한 PostgreSQL 서비스의 DATABASE_URL 사용

## 확인 체크리스트

- [ ] Worker 로그: "저장 완료!" 메시지 확인
- [ ] 데이터베이스: SQL 쿼리로 포스트 수 확인
- [ ] Streamlit Variables: DATABASE_URL 설정 확인
- [ ] Streamlit 재시작: Redeploy 실행
- [ ] 브라우저: 새로고침 (Ctrl+R)

## 빠른 테스트

Railway PostgreSQL 서비스의 **Data** 탭에서:

```sql
-- 이 쿼리가 결과를 반환하면 데이터는 있음
SELECT COUNT(*) FROM raw_reddit_posts;
```

결과가 0이면 → Worker 문제
결과가 0이 아니면 → Streamlit 문제
