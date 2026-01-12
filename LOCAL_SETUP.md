# 로컬 실행 가이드

이 문서는 프로젝트를 로컬 환경에서 실행하기 위한 단계별 가이드입니다.

## 사전 요구사항

- Python 3.11 이상
- PostgreSQL 데이터베이스 (로컬 또는 원격)
- Git

## 1단계: 가상환경 설정

```bash
# 프로젝트 루트 디렉토리로 이동
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate

# 가상환경 활성화 (Windows)
# .venv\Scripts\activate
```

## 2단계: 의존성 설치

```bash
# pip 업그레이드 (선택사항)
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt
```

## 3단계: 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# .env 파일 생성
touch .env
```

`.env` 파일 내용 예시:

```env
# 데이터베이스 연결 (필수)
# Railway PostgreSQL 사용 시
DATABASE_URL=postgresql://postgres:password@host:port/database

# 또는 개별 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kitchen_seasonal_db
DB_USER=postgres
DB_PASSWORD=your_password

# OpenAI API 키 (선택사항 - 일부 기능에 필요)
OPENAI_API_KEY=sk-...

# 환경 설정
ENVIRONMENT=development
LOG_LEVEL=INFO
PORT=8502
```

**참고**: 
- Railway 데이터베이스를 사용하는 경우, Railway 대시보드에서 `DATABASE_URL`을 복사하여 사용하세요.
- 로컬 PostgreSQL을 사용하는 경우, 데이터베이스를 먼저 생성해야 합니다.

## 4단계: Streamlit 대시보드 실행

### 방법 1: 스크립트 사용 (권장)

```bash
# 실행 권한 부여 (처음 한 번만)
chmod +x run_streamlit_local.sh

# 실행
./run_streamlit_local.sh
```

### 방법 2: 직접 실행

```bash
# 가상환경이 활성화되어 있는지 확인
streamlit run web/app.py --server.port 8502
```

### 방법 3: 환경 변수와 함께 실행

```bash
# DATABASE_URL을 직접 지정하여 실행
DATABASE_URL="postgresql://..." streamlit run web/app.py --server.port 8502
```

## 5단계: 브라우저에서 접속

실행 후 브라우저에서 다음 주소로 접속하세요:

```
http://localhost:8502
```

## 문제 해결

### 가상환경이 활성화되지 않는 경우

```bash
# Python 경로 확인
which python3

# 가상환경 재생성
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
```

### 의존성 설치 오류

```bash
# pip 업그레이드 후 재시도
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 데이터베이스 연결 오류

1. `.env` 파일의 `DATABASE_URL` 확인
2. 데이터베이스 서버가 실행 중인지 확인
3. 연결 정보(호스트, 포트, 사용자명, 비밀번호) 확인

```bash
# 데이터베이스 연결 테스트 (스크립트가 있다면)
python scripts/db_smoke_test.py
```

### 포트가 이미 사용 중인 경우

```bash
# 다른 포트로 실행 (예: 8503, 8504 등)
streamlit run web/app.py --server.port 8503
```

또는 기존 프로세스 종료:

```bash
# 포트 8502를 사용하는 프로세스 찾기
lsof -ti:8502

# 프로세스 종료
kill -9 $(lsof -ti:8502)
```

## 추가 정보

- 대시보드 중지: 터미널에서 `Ctrl + C` 누르기
- 로그 확인: 터미널에 출력되는 로그 메시지 확인
- 환경 변수 확인: `.env` 파일이 올바른 위치에 있는지 확인 (프로젝트 루트)

## 다음 단계

대시보드가 정상적으로 실행되면:
- 데이터 수집 파이프라인 실행 (`worker/` 폴더 참고)
- 데이터 분석 및 클러스터링 실행
- 대시보드에서 결과 확인

자세한 내용은 `README.md`를 참고하세요.
