# Railway Worker 재배포 및 실행 단계

## ✅ 1단계 완료: Variables 설정
Railway Worker 서비스의 Variables에 다음을 설정했습니다:
- `DATABASE_URL`
- `APIFY_API_TOKEN`
- `WORKER_MODE=save_keywords`
- `WORKER_ONCE=true`

## 🔄 2단계: Worker 서비스 재배포

### 방법 A: Railway 대시보드에서 재배포 (권장)

1. **Railway 대시보드 접속**
   - https://railway.app/ 접속
   - 프로젝트 선택

2. **Worker 서비스 선택**
   - Worker 서비스 클릭

3. **재배포 실행**
   - **"Deployments"** 탭 클릭
   - 최신 배포 옆의 **"..."** 메뉴 클릭
   - **"Redeploy"** 선택
   - 또는 **"Settings"** 탭에서 **"Redeploy"** 버튼 클릭

4. **배포 진행 확인**
   - 배포가 시작되면 로그가 자동으로 표시됩니다
   - 빌드 및 배포 완료까지 대기 (보통 1-3분)

### 방법 B: Railway CLI 사용

```bash
# Railway CLI 설치 (없는 경우)
npm i -g @railway/cli

# 로그인 및 프로젝트 연결
railway login
railway link

# Worker 서비스 재배포
railway up --service worker
```

### 방법 C: Git Push로 자동 재배포

Railway가 GitHub와 연결되어 있다면:
```bash
git add .
git commit -m "Add save_keywords mode to worker"
git push
```

Railway가 자동으로 감지하여 재배포합니다.

## 📊 3단계: 로그 확인

1. **Worker 서비스의 "Logs" 탭 클릭**
2. 다음 로그가 보여야 합니다:

```
Worker 시작
  모드: save_keywords
  간격: 3600초
  한 번만 실행: True
  Dry run: False
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
  Fetched 200 items (total: 200)
  Processing 200 items...
  ✅ spring dinner ideas: 150 posts, 300 comments
...
```

## ✅ 4단계: 실행 완료 확인

로그에서 다음 메시지를 확인하세요:

```
============================================================
저장 완료!
  처리된 키워드: 20/20
  총 포스트: XXXX
  총 댓글: XXXX
============================================================
```

## 🔄 5단계: Variables 복구 (선택사항)

일회성 실행이 완료되면, Worker가 정상 모드로 동작하도록 Variables를 복구하세요:

1. Worker 서비스의 **Variables** 탭으로 이동
2. 다음 변수 삭제 또는 변경:
   - `WORKER_MODE` 삭제 (또는 `collect`로 변경)
   - `WORKER_ONCE` 삭제 (또는 `false`로 변경)
3. Worker 서비스가 자동으로 재시작됩니다

## 🐛 문제 해결

### 배포가 실패하는 경우

1. **로그 확인**: Deployments 탭에서 실패한 배포의 로그 확인
2. **빌드 오류**: Dockerfile이나 requirements.txt 문제 확인
3. **환경 변수**: Variables가 올바르게 설정되었는지 확인

### 실행 중 오류 발생

1. **로그 확인**: Logs 탭에서 오류 메시지 확인
2. **APIFY_API_TOKEN**: Apify 콘솔에서 토큰이 활성화되어 있는지 확인
3. **DATABASE_URL**: PostgreSQL 서비스가 실행 중인지 확인

### 모듈을 찾을 수 없음

- `save_all_keywords_api.py` 파일이 프로젝트 루트에 있는지 확인
- Git에 커밋되어 있는지 확인 (Railway는 Git에서 코드를 가져옵니다)

## 📝 참고사항

- 재배포는 보통 1-3분 소요됩니다
- Variables 변경 시 Worker가 자동으로 재시작됩니다
- `WORKER_ONCE=true`로 설정하면 한 번 실행 후 종료됩니다
- 로그는 실시간으로 확인할 수 있습니다
