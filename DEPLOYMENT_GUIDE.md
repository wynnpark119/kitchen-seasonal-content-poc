# Railway 배포 가이드

## 배포 완료 사항

✅ 변경사항 커밋 및 GitHub 푸시 완료
- OpenAI API 키 로드 수정
- DB summary 제거, GPT 요약만 사용
- 환경 변수 로드 개선

## Railway 배포 단계

### 1. Railway 대시보드 접속

1. [Railway](https://railway.app)에 로그인
2. 프로젝트 선택 또는 새 프로젝트 생성

### 2. GitHub 저장소 연결 확인

- 프로젝트에 GitHub 저장소가 연결되어 있는지 확인
- 연결되어 있으면 자동으로 배포가 시작됩니다
- 연결되어 있지 않으면:
  1. "New" → "GitHub Repo" 선택
  2. `wynnpark119/kitchen-seasonal-content-poc` 저장소 선택

### 3. 환경 변수 설정 확인

Streamlit 서비스의 **Variables** 탭에서 다음 환경 변수가 설정되어 있는지 확인:

#### 필수 환경 변수

- `DATABASE_URL`: PostgreSQL 연결 URL (PostgreSQL 서비스에서 자동 주입됨)
- `OPENAI_API_KEY`: OpenAI API 키 (필수)
- `PORT`: Railway가 자동 설정 (수동 설정 불필요)

#### 설정 방법

1. Streamlit 서비스 선택
2. **Variables** 탭 클릭
3. `OPENAI_API_KEY` 추가:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   ```

### 4. 배포 확인

#### 자동 배포 (GitHub 연동 시)

- GitHub에 푸시하면 Railway가 자동으로 배포를 시작합니다
- **Deployments** 탭에서 배포 상태 확인

#### 수동 배포

1. **Settings** 탭 → **Redeploy** 클릭
2. 또는 **Deployments** 탭 → **Redeploy** 클릭

### 5. 배포 후 확인

#### 로그 확인

**Logs** 탭에서 다음 메시지 확인:

```
✅ 정상 시작:
Starting Streamlit...
PORT=8501
DATABASE_URL=postgresql://...
```

#### 서비스 URL 확인

**Settings** 탭에서 **Generate Domain** 클릭하여 공개 URL 생성

또는 **Networking** 탭에서 도메인 확인

### 6. 기능 테스트

배포된 서비스에 접속하여:

1. **🧠 Reddit 토픽 분석** 탭 확인
2. 클러스터를 펼쳐서 GPT 요약이 표시되는지 확인
3. "⚠️ OpenAI API 키가 설정되지 않아 GPT 요약을 생성할 수 없습니다." 경고가 사라졌는지 확인

## 문제 해결

### 배포 실패 시

1. **Logs** 탭에서 에러 메시지 확인
2. 일반적인 문제:
   - `DATABASE_URL` 없음 → PostgreSQL 서비스 연결 확인
   - `OPENAI_API_KEY` 없음 → Variables에 추가
   - 포트 충돌 → Railway가 자동 처리 (문제 없음)

### GPT 요약이 표시되지 않는 경우

1. **Variables** 탭에서 `OPENAI_API_KEY` 확인
2. **Logs** 탭에서 OpenAI API 호출 에러 확인
3. API 키가 유효한지 확인 (OpenAI 대시보드)

### 데이터베이스 연결 실패

1. PostgreSQL 서비스가 실행 중인지 확인
2. `DATABASE_URL` 환경 변수가 올바른지 확인
3. PostgreSQL 서비스의 **Variables** 탭에서 `DATABASE_URL` 복사

## 배포 체크리스트

- [ ] GitHub에 코드 푸시 완료
- [ ] Railway 프로젝트에 GitHub 저장소 연결됨
- [ ] Streamlit 서비스 생성됨
- [ ] PostgreSQL 서비스 연결됨
- [ ] `DATABASE_URL` 환경 변수 설정됨 (자동)
- [ ] `OPENAI_API_KEY` 환경 변수 설정됨
- [ ] 배포 완료 및 서비스 실행 중
- [ ] 공개 URL 접속 가능
- [ ] GPT 요약 기능 정상 작동

## 다음 단계

배포가 완료되면:
1. 공개 URL을 팀에 공유
2. 정기적으로 로그 모니터링
3. 필요시 Worker 서비스도 배포 (데이터 수집/분석 파이프라인)
