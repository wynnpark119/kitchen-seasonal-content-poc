# 데이터베이스 연결 설정 분석

## 현재 상태

### ✅ 일관성 있는 부분

1. **환경 변수 읽기 순서**: 모든 파일에서 동일한 순서로 환경 변수를 읽음
   ```
   DATABASE_URL → RAILWAY_DATABASE_URL → POSTGRES_URL → POSTGRES_PRIVATE_URL
   ```

2. **동일한 데이터베이스 URL 사용**: 모든 모듈이 같은 환경 변수를 참조하므로 같은 데이터베이스를 바라봄

### ⚠️ 불일치 부분

1. **.env 파일 로드 방식**:
   - ✅ `common/config.py`: `.env` 파일을 로드함 (`load_dotenv()`)
   - ❌ `worker/pipeline/db.py`: `.env` 파일을 로드하지 않음 (`os.getenv()`만 사용)
   - ❌ `web/db_queries.py`: `.env` 파일을 로드하지 않음 (`os.getenv()`만 사용)

2. **데이터베이스 연결 라이브러리**:
   - `common/db.py`: SQLAlchemy 사용 (하지만 실제로 사용되는 곳이 없음)
   - `worker/pipeline/db.py`: psycopg2 사용 (Connection pool)
   - `web/db_queries.py`: psycopg2 사용 (직접 연결)

## 파일별 상세 분석

### 1. `common/config.py`
```python
# .env 파일 로드
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = (
    os.getenv("DATABASE_URL") or 
    os.getenv("RAILWAY_DATABASE_URL") or
    os.getenv("POSTGRES_URL") or
    os.getenv("POSTGRES_PRIVATE_URL")
)
```
- ✅ `.env` 파일을 로드함
- ⚠️ 하지만 실제로 `common/db.py`만 사용하고, 다른 곳에서는 사용하지 않음

### 2. `common/db.py`
```python
from common.config import DATABASE_URL

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
```
- ✅ `common/config.py`의 DATABASE_URL 사용
- ⚠️ SQLAlchemy를 사용하지만 실제로 사용되는 곳이 없음 (Streamlit이나 Worker에서 사용 안 함)

### 3. `worker/pipeline/db.py`
```python
# .env 파일 로드 없음
database_url = (
    os.getenv("DATABASE_URL") or 
    os.getenv("RAILWAY_DATABASE_URL") or
    os.getenv("POSTGRES_URL") or
    os.getenv("POSTGRES_PRIVATE_URL")
)
```
- ❌ `.env` 파일을 로드하지 않음
- ✅ psycopg2 Connection pool 사용
- ✅ Worker 파이프라인에서 실제 사용됨

### 4. `web/db_queries.py`
```python
# .env 파일 로드 없음
database_url = (
    os.getenv("DATABASE_URL") or 
    os.getenv("RAILWAY_DATABASE_URL") or 
    os.getenv("POSTGRES_URL") or
    os.getenv("POSTGRES_PRIVATE_URL")
)
```
- ❌ `.env` 파일을 로드하지 않음
- ✅ psycopg2 직접 연결 사용
- ✅ Streamlit 대시보드에서 실제 사용됨

### 5. `save_keywords_local.py`, `save_all_keywords_api.py` 등
- `worker.pipeline.db` 모듈을 import하여 사용
- 따라서 `worker/pipeline/db.py`의 방식을 따름

## 결론

### ✅ 같은 데이터베이스를 바라봄
모든 모듈이 동일한 환경 변수 이름을 사용하므로, 환경 변수가 제대로 설정되어 있다면 같은 데이터베이스를 바라봅니다.

### ⚠️ 개선 필요 사항

1. **.env 파일 로드 불일치**:
   - 로컬 개발 시 `.env` 파일이 있어도 `worker/pipeline/db.py`와 `web/db_queries.py`에서 읽지 못할 수 있음
   - 해결: 모든 파일에서 `.env` 파일을 로드하도록 통일

2. **중복 코드**:
   - 환경 변수 읽기 로직이 여러 파일에 중복됨
   - 해결: 공통 함수로 추출하여 재사용

## 권장 수정 사항

1. `worker/pipeline/db.py`에 `.env` 파일 로드 추가
2. `web/db_queries.py`에 `.env` 파일 로드 추가
3. (선택) 환경 변수 읽기 로직을 공통 모듈로 추출
