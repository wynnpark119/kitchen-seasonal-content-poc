# Railway Worker에서 키워드 데이터 저장 실행 가이드

## 1단계: Railway Worker 서비스 Variables 설정

1. **Railway 대시보드 접속**: https://railway.app/
2. 프로젝트 선택
3. **Worker 서비스** 클릭
4. **Variables** 탭 클릭
5. 다음 변수들을 추가/수정:

### 필수 변수

```
DATABASE_URL=postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@postgres-tezk.railway.internal:5432/railway
APIFY_API_TOKEN=your-apify-token-here
```

### 실행 모드 설정 (일회성 실행)

```
WORKER_MODE=save_keywords
WORKER_ONCE=true
```

**참고**: 
- `WORKER_MODE=save_keywords`: 키워드 데이터 저장 모드
- `WORKER_ONCE=true`: 한 번만 실행하고 종료

## 2단계: Worker 서비스 재배포 또는 재시작

Variables를 설정한 후:
1. Worker 서비스의 **"Deployments"** 탭에서
2. **"Redeploy"** 클릭하거나
3. 서비스가 자동으로 재시작됩니다

## 3단계: 로그 확인

1. Worker 서비스의 **"Logs"** 탭에서 실행 로그 확인
2. 다음과 같은 로그가 보여야 합니다:

```
Worker 시작
  모드: save_keywords
  한 번만 실행: True
...
✅ Apify 클라이언트 초기화 완료
✅ 데이터베이스 연결 성공
Pipeline run 생성: run_id=1

============================================================
총 20개 키워드 데이터 저장 시작
============================================================

[1/20] Processing: spring dinner ideas
  Dataset ID: Chej96NJu2xomUrg1
  Dataset has 200 items
  ...
```

## 실행 완료 확인

로그에서 다음 메시지를 확인하세요:

```
============================================================
저장 완료!
  처리된 키워드: 20/20
  총 포스트: XXXX
  총 댓글: XXXX
============================================================
```

## 문제 해결

### APIFY_API_TOKEN 오류

- Apify 콘솔에서 토큰 확인: https://console.apify.com/
- Settings > Integrations > API tokens
- 토큰이 활성화되어 있는지 확인

### DATABASE_URL 오류

- Railway PostgreSQL 서비스의 Variables 탭에서 `DATABASE_URL` 확인
- 내부 URL 형식: `postgresql://...@postgres-tezk.railway.internal:5432/railway`

### 모듈을 찾을 수 없음

- `save_all_keywords_api.py` 파일이 프로젝트 루트에 있는지 확인
- Worker 서비스가 최신 코드로 배포되었는지 확인

## 실행 후 Variables 복구

일회성 실행이 완료되면:

1. `WORKER_MODE`를 원래 값으로 변경 (예: `collect`)
2. `WORKER_ONCE`를 `false`로 변경 (또는 삭제)
3. Worker 서비스 재배포

또는 Variables에서 `WORKER_MODE`와 `WORKER_ONCE`를 삭제하면 기본값으로 동작합니다.

## 대안: Railway CLI 사용

Railway CLI를 사용하면 Variables 설정 없이도 실행할 수 있습니다:

```bash
# Railway CLI 설치
npm i -g @railway/cli

# 로그인 및 프로젝트 연결
railway login
railway link

# 환경 변수 설정 후 실행
railway variables set DATABASE_URL="postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@postgres-tezk.railway.internal:5432/railway"
railway variables set APIFY_API_TOKEN="your-token"
railway variables set WORKER_MODE="save_keywords"
railway variables set WORKER_ONCE="true"

# Worker 서비스에서 실행
railway run python -m worker.main
```
