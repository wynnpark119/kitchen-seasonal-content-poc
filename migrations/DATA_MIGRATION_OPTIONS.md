# 데이터베이스 마이그레이션 옵션

## 상황 정리

### 옵션 1: Railway에 스키마만 생성 (빈 DB)
- **장점**: 빠르게 시작 가능, 테스트 환경 분리
- **단점**: 기존 데이터를 다시 수집해야 함
- **적합한 경우**: 
  - Railway에서 처음부터 시작
  - 기존 데이터가 중요하지 않음
  - 테스트 데이터만 있음

### 옵션 2: 로컬 DB 데이터를 Railway로 이전
- **장점**: 기존 데이터 유지, 시간 절약
- **단점**: 덤프/복원 과정 필요
- **적합한 경우**:
  - 기존에 수집한 데이터가 중요함
  - 분석 결과가 이미 있음
  - 시간을 절약하고 싶음

---

## 옵션 2 선택 시: 로컬 → Railway 데이터 이전

### 1단계: 로컬 DB 덤프

```bash
# 로컬 DATABASE_URL 확인
# .env 파일 또는 환경 변수에서 확인
export LOCAL_DB_URL="postgresql://user:password@localhost:5432/kitchen_seasonal_db"

# 전체 DB 덤프
pg_dump $LOCAL_DB_URL -F c -f local_db_dump.dump

# 또는 SQL 형식으로 덤프
pg_dump $LOCAL_DB_URL -f local_db_dump.sql
```

### 2단계: Railway DB 스키마 생성

Railway Query 탭에서 `migrations/ALL_MIGRATIONS.sql` 실행 (스키마만 생성)

### 3단계: Railway DB에 데이터 복원

```bash
# Railway 공개 DATABASE_URL 확인 (Railway 대시보드에서)
export RAILWAY_DB_URL="postgresql://postgres:password@public-host:port/railway"

# 덤프 파일 복원
pg_restore -d $RAILWAY_DB_URL local_db_dump.dump

# 또는 SQL 파일 복원
psql $RAILWAY_DB_URL < local_db_dump.sql
```

---

## 빠른 확인: 로컬 DB에 데이터가 있는지 확인

```bash
# 로컬 DATABASE_URL 설정
export LOCAL_DB_URL="postgresql://user:password@localhost:5432/kitchen_seasonal_db"

# 테이블 목록 확인
psql $LOCAL_DB_URL -c "\dt"

# 데이터 개수 확인
psql $LOCAL_DB_URL -c "
SELECT 
    'raw_reddit_posts' as table_name, COUNT(*) as count FROM raw_reddit_posts
UNION ALL
SELECT 'raw_serp_aio', COUNT(*) FROM raw_serp_aio
UNION ALL
SELECT 'clusters', COUNT(*) FROM clusters
UNION ALL
SELECT 'topic_qa_briefs', COUNT(*) FROM topic_qa_briefs;
"
```

---

## 추천 방법

**기존 데이터가 중요하다면**: 옵션 2 (데이터 이전)
**새로 시작한다면**: 옵션 1 (스키마만 생성)

어떤 옵션을 선택하시겠습니까?
