# Railway 콘솔에서 직접 실행하기

Railway CLI에서 Worker 서비스를 찾지 못했습니다. Railway 콘솔에서 직접 실행하는 것이 가장 확실한 방법입니다.

## 실행 방법

### 1단계: Railway 콘솔 접속
https://railway.app 접속

### 2단계: 프로젝트 및 서비스 선택
1. 프로젝트: `kitchen-seasonal-content-poc` 선택
2. 서비스 선택:
   - **Worker 서비스**가 있으면 Worker 선택
   - 없으면 **새 서비스 생성** 또는 **기존 서비스** 사용

### 3단계: 환경 변수 설정
1. 선택한 서비스 → **Variables** 탭
2. **New Variable** 클릭
3. 다음 추가:
   ```
   Key: APIFY_API_TOKEN
   Value: your-apify-api-token-here
   ```
4. **Add** 클릭

### 4단계: 실행
#### 방법 A: Deployments에서 실행
1. 서비스 → **Deployments** 탭
2. **New Deployment** 클릭
3. **Command** 입력:
   ```
   python run_parallel_collection.py
   ```
4. **Deploy** 클릭

#### 방법 B: 서비스 설정에서 실행
1. 서비스 → **Settings** 탭
2. **Start Command** 변경:
   ```
   python run_parallel_collection.py
   ```
3. 서비스 재시작 또는 새 Deployment 생성

## 실행 확인

### Railway 로그
- 서비스 → **Logs** 탭에서 실시간 확인
- 다음과 같은 메시지가 보여야 합니다:
  ```
  Pipeline run created: run_id=XXX
  Starting parallel Reddit collection for 20 keywords
  ✅ Started: spring dinner ideas (Run ID: ...)
  ```

### Apify 콘솔
- https://console.apify.com → **Runs** 탭
- 20개 Run이 동시에 실행되는 것 확인

## 문제 해결

### 서비스를 찾을 수 없는 경우
- Railway 콘솔에서 새 서비스를 생성하거나
- 기존 서비스(예: streamlit)에서 실행 가능

### 환경 변수 설정
- Railway 콘솔 → Variables 탭에서 직접 설정하는 것이 가장 확실합니다

### 파일 경로
- Railway는 프로젝트 루트에서 실행되므로 `run_parallel_collection.py`가 루트에 있어야 합니다
- 현재 파일 위치: ✅ `/Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc/run_parallel_collection.py`

---

**Railway 콘솔에서 실행하는 것이 가장 확실한 방법입니다! 🚀**
