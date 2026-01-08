# kitchen-seasonal-content-poc

Reddit / Google SERP / GSC 데이터를 분석하는 파이프라인과 Streamlit 대시보드를 개발하는 PoC 프로젝트입니다.

## 기술 스택

- Python 3.11
- Streamlit (대시보드)
- PostgreSQL (데이터베이스)
- Railway (배포 플랫폼)
- Docker (컨테이너화)

## 개발 가이드

이 프로젝트는 PoC이며, **SPEC.md**와 **TASKS.md**를 기준으로 개발합니다.

## 프로젝트 구조

```
kitchen-seasonal-content-poc/
├── web/            # Streamlit 대시보드
├── worker/         # 데이터 수집/분석 파이프라인
├── common/         # DB, 설정, 공용 유틸
├── data/           # 임시 CSV, 중간 산출물 (gitignore 대상)
├── tests/          # 최소 테스트/검증 스크립트
├── migrations/     # DB DDL / 마이그레이션 SQL
├── Dockerfile      # Streamlit 서비스용
├── worker/Dockerfile  # Worker 서비스용
├── requirements.txt
├── railway.json    # Railway Streamlit 서비스 설정
├── railway-worker.json  # Railway Worker 서비스 설정
├── .env.example
└── README.md
```

## Railway 배포

### 1. Railway 프로젝트 생성

1. [Railway](https://railway.app)에 로그인
2. "New Project" 생성
3. GitHub 저장소 연결

### 2. PostgreSQL 데이터베이스 추가

1. Railway 프로젝트에서 "New" → "Database" → "PostgreSQL" 선택
2. 데이터베이스가 생성되면 `DATABASE_URL` 환경 변수가 자동으로 설정됩니다

### 3. Streamlit 서비스 배포

1. "New" → "GitHub Repo" 선택
2. 저장소 선택 후 배포
3. Railway가 `Dockerfile`을 자동 감지하여 빌드
4. 환경 변수 설정:
   - `PORT=8501` (자동 설정됨)
   - `DATABASE_URL` (PostgreSQL 플러그인에서 자동 주입)

### 4. Worker 서비스 배포 (선택사항)

1. 동일한 프로젝트에서 "New" → "GitHub Repo" 선택
2. 같은 저장소 선택
3. Railway 설정에서:
   - Dockerfile 경로: `worker/Dockerfile`
   - 시작 명령: `python -m worker.main`
   - 또는 `railway-worker.json` 사용

### 5. 환경 변수 설정

Railway 대시보드에서 각 서비스의 "Variables" 탭에서 환경 변수 설정:
- `.env.example` 파일 참고

## 로컬 개발

### 1. 가상환경 설정

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 값 입력
```

### 4. Streamlit 실행

```bash
streamlit run web/app.py
```

### 5. Worker 실행

```bash
python -m worker.main
```

## 주의사항

- `.env` 파일은 절대 커밋하지 마세요 (`.gitignore`에 포함됨)
- `data/` 폴더는 로컬 개발용이며 커밋되지 않습니다
- Railway에서 PostgreSQL 플러그인 사용 시 `DATABASE_URL`이 자동으로 주입됩니다
