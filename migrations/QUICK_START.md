# 빠른 마이그레이션 실행 가이드

## 문제
제공하신 DATABASE_URL은 내부 호스트명(`railway.internal`)이므로 로컬에서 직접 접근할 수 없습니다.

## 해결 방법

### 방법 1: Railway 대시보드에서 공개 DATABASE_URL 확인 (가장 간단)

1. Railway 대시보드 → PostgreSQL 서비스 (`Postgres-tezK`)
2. **"Connect"** 또는 **"Data"** 탭 클릭
3. **"Public Network"** 섹션에서 연결 문자열 확인
4. 공개 호스트명이 포함된 DATABASE_URL 복사
   - 예: `postgresql://postgres:패스워드@xxxx.proxy.rlwy.net:5432/railway`

5. 로컬에서 실행:
```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
export DATABASE_URL="공개_DATABASE_URL_여기"
python3 migrations/run_migration.py
```

---

### 방법 2: Railway CLI 사용

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# Railway 프로젝트 연결 (처음 한 번만)
railway link

# PostgreSQL 서비스 선택
railway service postgres-tezk

# 마이그레이션 실행 (Railway CLI가 DATABASE_URL 자동 주입)
python3 migrations/run_migration.py
```

또는 스크립트 사용:
```bash
./migrations/run_migration_railway.sh
```

---

### 방법 3: Railway 대시보드에서 직접 실행 (가능한 경우)

일부 Railway 버전에서는 PostgreSQL 서비스에 **"Query"** 또는 **"SQL Editor"** 탭이 있을 수 있습니다.

1. Railway 대시보드 → PostgreSQL 서비스
2. **"Query"** 또는 **"SQL Editor"** 탭 확인
3. `migrations/ALL_MIGRATIONS.sql` 내용 복사하여 실행

---

## 추천

**가장 간단한 방법**: 방법 1 (공개 DATABASE_URL 사용)

Railway 대시보드에서 **"Public Network"** 연결 문자열을 확인하시면 바로 실행할 수 있습니다!
