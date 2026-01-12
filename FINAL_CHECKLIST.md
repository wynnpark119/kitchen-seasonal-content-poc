# ✅ Railway 실행 전 최종 체크리스트

## 필수 확인 사항

### 1. 파일 확인 ✅
- [x] `run_parallel_collection.py` - 메인 실행 스크립트
- [x] `worker/pipeline/collect_reddit_parallel.py` - 병렬 수집 모듈
- [x] `requirements.txt`에 `apify-client` 포함됨

### 2. Railway 환경 변수 설정

Railway 콘솔 → Worker 서비스 → Variables에서 확인:

```
✅ DATABASE_URL 또는 RAILWAY_DATABASE_URL (이미 설정되어 있을 것)
✅ APIFY_API_TOKEN=your-apify-api-token-here (추가 필요)
```

### 3. 실행 방법 선택

#### 방법 A: Railway CLI (터미널에서)
```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
railway variables set APIFY_API_TOKEN=your-apify-api-token-here
railway run python run_parallel_collection.py
```

#### 방법 B: Railway 콘솔 (웹에서)
1. Railway 콘솔 접속: https://railway.app
2. 프로젝트 → Worker 서비스 선택
3. Variables 탭 → `APIFY_API_TOKEN` 추가
4. Deployments 탭 → New Deployment
5. Command: `python run_parallel_collection.py`
6. Deploy 클릭

## 실행 후 확인

### Railway 로그
- Worker 서비스 → Logs 탭
- 다음과 같은 메시지 확인:
  ```
  Pipeline run created: run_id=XXX
  Starting parallel Reddit collection for 20 keywords
  ✅ Started: spring dinner ideas (Run ID: ...)
  ...
  ```

### Apify 콘솔
- https://console.apify.com → Runs 탭
- 20개 Run이 동시에 실행되는 것 확인

### 데이터베이스
- 수집 완료 후 PostgreSQL에서 확인:
  ```sql
  SELECT keyword, COUNT(*) 
  FROM raw_reddit_posts 
  GROUP BY keyword 
  ORDER BY keyword;
  ```

## 예상 소요 시간

- **Run 시작**: 즉시 (20개 동시 시작)
- **각 Run 완료**: 키워드당 약 2-5분
- **전체 완료**: 약 30분~1시간
- **데이터 저장**: 완료 후 자동 저장

## 비용 예상

- Apify 사용 비용: Run당 약 $0.5-2
- 20개 Run: 약 $10-40 (실제 수집량에 따라 다름)

## 문제 해결

### APIFY_API_TOKEN 오류
```bash
railway variables set APIFY_API_TOKEN=your-apify-api-token-here
```

### 모듈 import 오류
- Railway Worker는 자동으로 `requirements.txt`를 설치합니다
- `apify-client`가 포함되어 있는지 확인

### 네트워크 오류
- Railway Worker는 안정적인 네트워크 환경을 제공합니다
- 문제가 지속되면 Railway 지원팀에 문의

## 성공 확인

실행이 성공하면 Railway 로그에 다음이 출력됩니다:

```
============================================================
병렬 수집 완료!
============================================================
수집된 포스트: XXXX개
수집된 댓글: XXXX개
처리된 키워드: 20개
시작된 Run: 20개
완료된 Run: 20개
```

---

**준비 완료! Railway에서 실행하세요! 🚀**
