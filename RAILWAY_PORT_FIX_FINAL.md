# Railway Streamlit 포트 문제 해결

## 문제
Streamlit이 Railway의 PORT 환경 변수를 읽지 못해 "Application failed to respond" 에러 발생

## 해결 방법

### 1. railway.json 수정 완료
`startCommand`에 `--server.port=${PORT:-8501}` 추가

### 2. Railway에서 재배포 필요

**Railway 대시보드에서:**
1. Streamlit 서비스 클릭
2. **"Settings"** 탭 클릭
3. **"Redeploy"** 버튼 클릭
4. 또는 **"Deployments"** 탭에서 최신 배포의 **"Redeploy"** 클릭

### 3. 재배포 후 확인

재배포 후:
- Streamlit 서비스 상태가 "Active"로 변경되는지 확인
- 로그에서 정상 시작 메시지 확인
- 대시보드 접속 테스트

---

## 변경 사항

### railway.json
```json
"startCommand": "streamlit run web/app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"
```

### Dockerfile
```dockerfile
CMD ["streamlit", "run", "web/app.py", "--server.address=0.0.0.0", "--server.port=${PORT:-8501}"]
```

---

## 다음 단계

1. **Git에 커밋 및 푸시** (변경사항 반영)
2. **Railway에서 재배포**
3. **대시보드 접속 테스트**
