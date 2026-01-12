# Railway PORT 환경 변수 문제 해결

## 문제
Streamlit 서비스가 `$PORT` 환경 변수를 문자열 그대로 읽어서 에러 발생:
```
Error: Invalid value for '--server.port' (env var: 'STREAMLIT_SERVER_PORT'): '$PORT' is not a valid integer.
```

## 해결 방법

### 1. Streamlit이 PORT 환경 변수를 자동으로 읽도록 설정

Streamlit은 기본적으로 `PORT` 환경 변수를 자동으로 읽습니다. 따라서 명시적으로 포트를 지정할 필요가 없습니다.

### 2. 수정된 파일

#### `railway.json`
```json
{
  "deploy": {
    "startCommand": "streamlit run web/app.py --server.address=0.0.0.0",
    ...
  }
}
```
- `--server.port` 옵션 제거
- Streamlit이 `PORT` 환경 변수를 자동으로 읽음

#### `.streamlit/config.toml`
```toml
[server]
headless = true
# port는 Railway의 PORT 환경 변수를 사용 (설정하지 않음)
enableCORS = false
enableXsrfProtection = false
```
- `port = 8501` 제거
- Streamlit이 환경 변수를 우선 사용

#### `Dockerfile`
```dockerfile
CMD ["streamlit", "run", "web/app.py", "--server.address=0.0.0.0"]
```
- 포트 지정 제거
- Streamlit이 `PORT` 환경 변수를 자동으로 읽음

## Railway 배포 확인

### 1. 재배포 대기
- GitHub 푸시 후 Railway가 자동으로 재배포 시작
- 약 2-3분 소요

### 2. 로그 확인
```bash
railway logs --tail 50 --service streamlit
```

### 3. 예상되는 성공 로그
```
Starting Container
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://0.0.0.0:8501
```

## 참고

- Railway는 `PORT` 환경 변수를 자동으로 설정합니다
- Streamlit은 `PORT` 환경 변수가 있으면 자동으로 사용합니다
- 명시적으로 포트를 지정하면 환경 변수 확장 문제가 발생할 수 있습니다
