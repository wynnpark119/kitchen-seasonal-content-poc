# 프로젝트 리팩토링 결과 보고서

작업 일시: 2024년
작업 목표: POC 단계 코드를 최종 스펙 기준으로 정리 및 성능/안정성 개선

---

## (A) 수정된 파일 목록

### 1. UI/대시보드 구조 수정
- **web/app.py**: 탭 구조 제거, 바로 3개 화면 표시로 변경
  - Before: `st.tabs()` 사용하여 탭 구조
  - After: `st.header()`로 각 섹션을 바로 표시

### 2. OpenAI API 키 통합
- **generate_master_topics_console.py**: `common/openai_client.py` 사용하도록 변경
  - Before: 자체 `get_openai_client()` 함수 사용
  - After: `common.openai_client.get_openai_client()` 사용

### 3. DB 커넥션 풀 개선
- **web/db_queries.py**: SQLAlchemy engine 기반 커넥션 풀 사용
  - Before: 매번 `psycopg2.connect()` 호출하여 새 연결 생성
  - After: `common.db.engine.raw_connection()` 사용하여 커넥션 풀 재사용

### 4. 서비스 레이어 개선
- **services/clustering_service.py**: numpy 타입 변환 유틸리티 추가
  - `to_python_int()` 함수 추가하여 numpy 타입을 Python int로 변환
  - `get_representative_posts()` 메서드에서 자동 타입 변환 처리

- **web/views/clustering_results.py**: numpy 타입 변환 로직 제거
  - Before: 뷰 레이어에서 numpy 타입 변환 처리
  - After: 서비스 레이어에서 처리하도록 변경

---

## (B) 제거된 화면/기능 목록

### 제거된 화면
- **Overview 탭**: 완전히 제거됨
  - 탭 구조 자체가 제거되어 Overview 탭도 함께 제거됨

### 제거된 기능
- **탭 네비게이션**: `st.tabs()` 사용 중단
- **헤더/소개 텍스트**: 대시보드 제목 외 설명 텍스트 제거

### 유지된 기능
- Clustering Results 화면 (기능 유지, 표시 방식만 변경)
- Trend Explorer 화면 (기능 유지, 표시 방식만 변경)
- Master Topics 화면 (기능 유지, 표시 방식만 변경)

---

## (C) OpenAI 호출 안정화 방식 요약

### 1. 단일 클라이언트 모듈 사용
- **common/openai_client.py**: 모든 GPT 호출에서 사용하는 단일 모듈
  - 싱글톤 패턴으로 클라이언트 인스턴스 재사용
  - API 키는 앱 시작 시 1회만 로드

### 2. API 키 로딩 우선순위
1. 환경변수 (`OPENAI_API_KEY`)
2. `.env` 파일 (존재 시)
3. 키가 없으면 `ValueError` 발생 (명확한 에러 메시지)

### 3. 키 검증
- `is_openai_available()`: API 키 사용 가능 여부 확인
- 키가 없으면 GPT 기능 자동 비활성화 (화면 깨짐 방지)

### 4. 통합된 사용처
- `services/gpt_service.py`: `common.openai_client.get_openai_client()` 사용
- `generate_master_topics_console.py`: `common.openai_client.get_openai_client()` 사용
- `web/views/clustering_results.py`: `common.openai_client.is_openai_available()` 사용

### 5. 에러 처리
- GPT 호출 실패 시:
  - 재시도 1회 (RateLimitError, APIConnectionError, APITimeoutError)
  - 실패 후 `None` 반환하여 화면 깨짐 방지
  - "Not available" placeholder 표시

---

## (D) 성능 개선 포인트 요약

### Before / After 비교

#### 1. DB 커넥션 관리

**Before:**
```python
def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url)  # 매번 새 연결 생성
```

**After:**
```python
from common.db import engine

def get_db_connection():
    return engine.raw_connection()  # 커넥션 풀에서 재사용
```

**기대 효과:**
- 연결 생성 오버헤드 감소 (약 50-100ms → 1-5ms)
- 동시 요청 처리 능력 향상
- DB 연결 수 제한으로 리소스 효율성 개선

#### 2. OpenAI 클라이언트 재사용

**Before:**
- 각 모듈에서 개별적으로 클라이언트 생성
- API 키를 매번 환경변수에서 읽음

**After:**
- `common/openai_client.py`에서 싱글톤 패턴으로 재사용
- API 키는 1회만 로드

**기대 효과:**
- 클라이언트 생성 오버헤드 제거
- 메모리 사용량 감소

#### 3. numpy 타입 변환

**Before:**
```python
# 뷰 레이어에서 매번 변환
import numpy as np
cluster_id_int = int(cluster_id) if not isinstance(cluster_id, (np.integer, np.int64)) else int(cluster_id)
```

**After:**
```python
# 서비스 레이어에서 한 번만 변환
def to_python_int(value):
    if isinstance(value, (np.integer, np.int64)):
        return int(value)
    return int(value)
```

**기대 효과:**
- 타입 변환 로직 중복 제거
- 코드 가독성 향상
- 유지보수 용이성 개선

#### 4. GPT 호출 재시도 로직

**Before:**
- 재시도 로직 없음 또는 불완전

**After:**
```python
# services/gpt_service.py
max_retries = 1
for attempt in range(max_retries + 1):
    try:
        response = self.client.chat.completions.create(...)
        return response.choices[0].message.content.strip()
    except (RateLimitError, APIConnectionError, APITimeoutError) as e:
        if attempt < max_retries:
            wait_time = (attempt + 1) * 2
            time.sleep(wait_time)
            continue
```

**기대 효과:**
- 일시적 네트워크 오류 자동 복구
- API 호출 성공률 향상

---

## (E) 현재 구조에서 다음에 확장하기 쉬운 지점

### 1. 서비스 레이어 확장
- **위치**: `services/` 디렉토리
- **현재 구조**:
  - `clustering_service.py`: 클러스터링 데이터 조회
  - `serp_service.py`: SERP 데이터 조회
  - `gpt_service.py`: GPT API 호출
- **확장 가능성**:
  - 새로운 데이터 소스 추가 시 새로운 서비스 클래스 추가만 하면 됨
  - 서비스 간 의존성 최소화로 독립적 확장 가능

### 2. 뷰 레이어 확장
- **위치**: `web/views/` 디렉토리
- **현재 구조**:
  - 각 화면별로 독립적인 `render_*()` 함수
  - `web/app.py`에서 간단히 임포트하여 사용
- **확장 가능성**:
  - 새로운 화면 추가 시 `web/views/new_view.py` 생성 후 `app.py`에 추가만 하면 됨
  - 화면 간 의존성 없음

### 3. DB 쿼리 확장
- **위치**: `web/db_queries.py`
- **현재 구조**:
  - SQLAlchemy engine 기반 커넥션 풀 사용
  - 각 쿼리 함수는 독립적으로 정의
- **확장 가능성**:
  - 새로운 쿼리 추가 시 함수만 추가하면 됨
  - 커넥션 풀 자동 활용

### 4. GPT 서비스 확장
- **위치**: `services/gpt_service.py`
- **현재 구조**:
  - `GPTService` 클래스에 메서드 추가 방식
  - 싱글톤 패턴으로 인스턴스 재사용
- **확장 가능성**:
  - 새로운 GPT 기능 추가 시 메서드만 추가하면 됨
  - 캐싱 로직 추가 가능 (향후 확장)

### 5. 설정 관리 확장
- **위치**: `common/config.py`
- **현재 구조**:
  - 환경변수 기반 설정 관리
  - `.env` 파일 지원
- **확장 가능성**:
  - 새로운 설정 추가 시 `common/config.py`에 변수만 추가하면 됨
  - 모든 모듈에서 `from common.config import *`로 사용 가능

### 6. 에러 처리 확장
- **현재 구조**:
  - 각 서비스/뷰에서 독립적인 에러 처리
  - GPT 실패 시 graceful fallback
- **확장 가능성**:
  - 공통 에러 핸들러 추가 가능
  - 로깅 시스템 통합 가능

---

## 추가 개선 사항

### 완료된 작업
1. ✅ UI 구조 단순화 (탭 제거)
2. ✅ OpenAI API 키 통합
3. ✅ DB 커넥션 풀 개선
4. ✅ numpy 타입 변환 중앙화
5. ✅ GPT 호출 재시도 로직 추가

### 향후 개선 가능 사항
1. **캐싱 시스템 추가**
   - GPT 호출 결과 캐싱 (DB 또는 파일 기반)
   - 클러스터링 결과 캐싱 (Streamlit `@st.cache_data` 활용)

2. **비동기 처리**
   - GPT 호출 비동기화 (asyncio 사용)
   - 배치 처리로 여러 카테고리 동시 처리

3. **로깅 시스템**
   - 구조화된 로깅 추가
   - 에러 추적 및 모니터링

4. **테스트 코드**
   - 서비스 레이어 단위 테스트
   - 통합 테스트

---

## 결론

POC 단계의 코드를 최종 스펙 기준으로 정리하고, 성능 및 안정성을 개선했습니다. 주요 변경 사항:

1. **UI 단순화**: 탭 제거, 결과 중심 화면 구성
2. **안정성 향상**: OpenAI API 키 통합, 에러 처리 개선
3. **성능 개선**: DB 커넥션 풀, 클라이언트 재사용
4. **코드 품질**: 서비스 레이어 분리, 타입 변환 중앙화

현재 구조는 확장 가능하며, 새로운 기능 추가 시 명확한 패턴을 따를 수 있습니다.
