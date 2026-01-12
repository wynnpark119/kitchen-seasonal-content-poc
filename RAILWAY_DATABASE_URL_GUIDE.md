# Railway DATABASE_URL 설정 가이드

## Railway에서 DATABASE_URL 찾는 방법

### 방법 1: Railway 대시보드에서 직접 확인

1. **Railway 대시보드 접속**
   - https://railway.app/ 접속
   - 로그인 후 프로젝트 선택

2. **PostgreSQL 서비스 찾기**
   - 프로젝트 내에서 PostgreSQL 서비스를 찾습니다
   - 서비스 이름: **"Postgres-tezK"** 또는 **"Postgres"**
   - 또는 "PostgreSQL" 또는 "Database"로 표시될 수 있습니다

3. **DATABASE_URL 복사**
   - PostgreSQL 서비스(예: "Postgres-tezK")를 클릭
   - **"Variables"** 탭 클릭
   - `DATABASE_URL` 변수를 찾아서 값을 복사합니다
   - 형식: `postgresql://user:password@host:port/database`
   - **참고**: Railway는 PostgreSQL 서비스를 추가하면 자동으로 `DATABASE_URL`을 생성합니다

### 방법 2: Railway CLI 사용

```bash
# Railway CLI 설치 (없는 경우)
npm i -g @railway/cli

# 로그인
railway login

# 프로젝트 선택
railway link

# DATABASE_URL 확인
railway variables
```

### 방법 3: Railway 서비스 Variables 탭에서 직접 설정

1. Railway 대시보드에서 프로젝트 선택
2. PostgreSQL 서비스 클릭
3. **"Variables"** 탭 클릭
4. `DATABASE_URL` 변수가 없으면 **"New Variable"** 클릭
5. Name: `DATABASE_URL`
6. Value: PostgreSQL 연결 문자열 입력
7. 저장

## 로컬에서 사용하기

### 환경 변수로 설정

```bash
# 터미널에서
export DATABASE_URL="postgresql://user:password@host:port/database"

# 또는 .env 파일에 추가
echo "DATABASE_URL=postgresql://user:password@host:port/database" >> .env
```

### 스크립트 실행

```bash
# 환경 변수 설정 후
python save_all_keywords_api.py
```

## Railway Worker 서비스에서 사용하기

Railway Worker 서비스의 **"Variables"** 탭에서 `DATABASE_URL`을 설정하면:
- Worker 서비스가 자동으로 이 변수를 사용합니다
- 별도로 export할 필요 없습니다

## 확인 방법

```bash
# Python으로 확인
python3 -c "import os; print(os.getenv('DATABASE_URL', 'Not set'))"

# 또는 스크립트 실행 시 자동 확인됨
python save_all_keywords_api.py
```

## 주의사항

- `DATABASE_URL`은 민감한 정보(비밀번호 포함)이므로 절대 Git에 커밋하지 마세요
- Railway의 Variables는 자동으로 환경 변수로 주입됩니다
- 로컬 개발 시에는 `.env` 파일을 사용하세요 (`.gitignore`에 포함되어 있음)
