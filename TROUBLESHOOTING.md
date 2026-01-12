# Streamlit 대시보드 데이터 미표시 문제 해결

## 문제: Streamlit 대시보드에서 Reddit Posts가 표시되지 않음

### 1단계: Worker 실행 상태 확인

Railway Worker 서비스의 **Logs** 탭에서 확인:

1. **실행 완료 확인**
   ```
   저장 완료!
     처리된 키워드: 20/20
     총 포스트: XXXX
     총 댓글: XXXX
   ```

2. **에러 확인**
   - 에러 메시지가 있는지 확인
   - 특히 `APIFY_API_TOKEN` 또는 `DATABASE_URL` 관련 에러

### 2단계: 데이터베이스 직접 확인

#### 방법 A: Railway PostgreSQL 서비스 사용

1. Railway 대시보드 → PostgreSQL 서비스 클릭
2. **"Data"** 탭 클릭
3. 다음 쿼리 실행:

```sql
-- 총 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY count DESC;

-- 최근 수집된 포스트 확인
SELECT keyword, title, upvotes, created_at 
FROM raw_reddit_posts 
ORDER BY created_at DESC 
LIMIT 10;
```

#### 방법 B: 로컬 스크립트 사용

```bash
# DATABASE_URL 설정 (Railway에서 복사)
export DATABASE_URL="postgresql://..."

# 스크립트 실행
python3 check_database_data.py
```

### 3단계: Streamlit 서비스 확인

#### Streamlit 서비스 Variables 확인

1. Railway 대시보드 → Streamlit 서비스 클릭
2. **Variables** 탭 확인:
   - `DATABASE_URL`이 설정되어 있는지 확인
   - Worker와 동일한 PostgreSQL 서비스를 사용하는지 확인

#### Streamlit 로그 확인

1. Streamlit 서비스 → **Logs** 탭
2. 데이터베이스 연결 에러 확인:
   - `DATABASE_URL not found`
   - `Connection refused`
   - `Table does not exist`

### 4단계: 데이터베이스 테이블 확인

Railway PostgreSQL 서비스의 **Data** 탭에서:

```sql
-- 테이블 존재 확인
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'raw_reddit%';

-- 테이블 구조 확인
\d raw_reddit_posts
```

### 5단계: Streamlit 재시작

데이터베이스에 데이터가 있는데 Streamlit에서 보이지 않으면:

1. Streamlit 서비스 → **Settings** 탭
2. **"Redeploy"** 클릭
3. 재배포 후 대시보드 새로고침

## 일반적인 문제와 해결책

### 문제 1: 데이터베이스에 데이터가 없음

**원인**: Worker가 아직 실행 중이거나 실패함

**해결**:
1. Worker 로그 확인
2. Worker가 완료될 때까지 대기
3. 에러가 있으면 수정 후 재실행

### 문제 2: Streamlit이 다른 데이터베이스에 연결됨

**원인**: Streamlit 서비스의 `DATABASE_URL`이 Worker와 다름

**해결**:
1. Streamlit 서비스 Variables에서 `DATABASE_URL` 확인
2. Worker와 동일한 PostgreSQL 서비스의 `DATABASE_URL` 사용
3. Streamlit 서비스 재시작

### 문제 3: 테이블이 존재하지 않음

**원인**: 마이그레이션이 실행되지 않음

**해결**:
1. Railway PostgreSQL 서비스 → **Data** 탭
2. `migrations/001_initial_schema.sql` 실행
3. 또는 Railway CLI 사용:
   ```bash
   railway run psql < migrations/001_initial_schema.sql
   ```

### 문제 4: 데이터는 있지만 Streamlit에서 보이지 않음

**원인**: Streamlit 캐시 문제 또는 쿼리 오류

**해결**:
1. Streamlit 대시보드 새로고침 (Ctrl+R 또는 Cmd+R)
2. Streamlit 서비스 재시작
3. Streamlit 로그에서 쿼리 에러 확인

## 확인 체크리스트

- [ ] Worker 로그에서 "저장 완료!" 메시지 확인
- [ ] 데이터베이스에 실제로 데이터가 있는지 확인 (SQL 쿼리)
- [ ] Streamlit 서비스의 `DATABASE_URL` 확인
- [ ] Streamlit 로그에서 에러 확인
- [ ] Streamlit 서비스 재시작 시도
- [ ] 브라우저 캐시 클리어 후 새로고침

## 추가 디버깅

### Streamlit에서 직접 쿼리 테스트

Streamlit 대시보드의 **Raw Data Explorer** 탭에서:
- 에러 메시지 확인
- "No Reddit posts available" 메시지 확인

### 데이터베이스 연결 테스트

```python
# Streamlit 서비스에서 실행
import os
import psycopg2

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM raw_reddit_posts")
print(cur.fetchone()[0])
```
