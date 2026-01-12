# 🚀 지금 바로 실행하기

## Railway에서 병렬 Reddit 수집 실행

### 방법 1: Railway CLI 사용 (가장 간단)

```bash
# 1. Railway CLI 로그인 (필요시)
railway login

# 2. 프로젝트 디렉토리로 이동
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

# 3. Railway 프로젝트 연결 (필요시)
railway link

# 4. 환경 변수 설정 확인
railway variables

# 5. APIFY_API_TOKEN이 없으면 추가
railway variables set APIFY_API_TOKEN=your-apify-api-token-here

# 6. 실행!
railway run python run_parallel_collection.py
```

### 방법 2: Railway 콘솔에서 직접 실행

1. **Railway 콘솔 접속**: https://railway.app
2. **프로젝트 선택** → **Worker 서비스** 선택
3. **Variables 탭**에서 환경 변수 확인/추가:
   ```
   APIFY_API_TOKEN=your-apify-api-token-here
   DATABASE_URL=<기존 값 유지>
   ```
4. **Deployments 탭** → **New Deployment**
5. **Command**에 입력: `python run_parallel_collection.py`
6. **Deploy** 클릭

### 방법 3: Worker 서비스 설정으로 자동 실행

1. **Railway 콘솔** → **Worker 서비스** → **Settings**
2. **Start Command**를 다음으로 변경:
   ```
   python run_parallel_collection.py
   ```
3. **Deploy** 또는 서비스 재시작

## 📊 실행 후 확인

### Railway 로그 확인
- Railway 콘솔 → Worker 서비스 → **Logs** 탭
- 실시간으로 진행 상황 확인 가능

### Apify 콘솔 확인
- https://console.apify.com 접속
- **Runs** 탭에서 20개 Run이 동시에 실행되는 것 확인

### 데이터베이스 확인
- 수집 완료 후 PostgreSQL에서 데이터 확인:
  ```sql
  SELECT COUNT(*) FROM raw_reddit_posts;
  SELECT keyword, COUNT(*) FROM raw_reddit_posts GROUP BY keyword;
  ```

## ⚠️ 주의사항

1. **비용**: Apify 사용 비용이 발생합니다 (각 Run당 약 $0.5-2)
2. **시간**: 20개 키워드 모두 완료까지 약 30분-1시간 소요될 수 있습니다
3. **네트워크**: Railway Worker는 안정적인 네트워크 환경을 제공합니다

## ✅ 성공 확인

실행이 성공하면 Railway 로그에 다음과 같은 메시지가 출력됩니다:

```
Pipeline run created: run_id=XXX
Starting parallel Reddit collection for 20 keywords
✅ Started: spring dinner ideas (Run ID: ...)
✅ Started: easy spring meals (Run ID: ...)
...
Started 20 parallel runs
Waiting for completion: spring dinner ideas (Run ID: ...)
✅ Completed: spring dinner ideas (Dataset ID: ...)
...
Parallel collection completed: XXXX posts, XXXX comments
Runs: 20/20 completed
```

## 🆘 문제 해결

### APIFY_API_TOKEN 오류
- Railway 환경 변수에 `APIFY_API_TOKEN`이 설정되어 있는지 확인

### DATABASE_URL 오류
- Railway 환경 변수에 `DATABASE_URL` 또는 `RAILWAY_DATABASE_URL`이 설정되어 있는지 확인

### 모듈 import 오류
- `apify-client`가 설치되어 있는지 확인 (requirements.txt에 포함됨)
