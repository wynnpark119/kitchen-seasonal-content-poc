# 빠른 시작 가이드: 모든 키워드 데이터 저장

## 필요한 것

1. **APIFY_API_TOKEN**: Apify API 토큰
2. **DATABASE_URL**: Railway PostgreSQL 연결 문자열

## 설정 방법

### 1. Apify API Token 가져오기

1. https://console.apify.com/ 접속
2. 로그인 후 **Settings** > **Integrations** > **API tokens** 클릭
3. API Token 복사 (또는 새로 생성)

```bash
export APIFY_API_TOKEN="your-apify-token-here"
```

### 2. Railway DATABASE_URL 가져오기

1. https://railway.app/ 접속
2. 프로젝트 선택
3. **PostgreSQL 서비스 클릭** (서비스 이름: "Postgres-tezK" 또는 "Postgres")
4. **Variables** 탭 클릭
5. `DATABASE_URL` 변수 값 복사
   - 형식: `postgresql://user:password@host:port/database`
   - Railway가 PostgreSQL 서비스를 추가하면 자동으로 생성됩니다

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

**또는** Railway Worker 서비스의 Variables 탭에서 `DATABASE_URL`을 직접 설정하면 자동으로 환경 변수로 주입됩니다 (별도 export 불필요)

## 실행

```bash
# 환경 변수 설정 확인
python3 -c "import os; print('APIFY_TOKEN:', '✅' if os.getenv('APIFY_API_TOKEN') else '❌'); print('DATABASE_URL:', '✅' if os.getenv('DATABASE_URL') or os.getenv('RAILWAY_DATABASE_URL') else '❌')"

# 스크립트 실행
python3 save_all_keywords_api.py
```

## 예상 출력

```
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

============================================================
저장 완료!
  처리된 키워드: 20/20
  총 포스트: 3000
  총 댓글: 6000
============================================================
```

## 문제 해결

### DATABASE_URL을 찾을 수 없음

- Railway 대시보드에서 PostgreSQL 서비스의 Variables 탭 확인
- `RAILWAY_DATABASE_URL` 환경 변수도 확인됨

### Apify API Token 오류

- Apify 콘솔에서 토큰이 활성화되어 있는지 확인
- 토큰에 필요한 권한이 있는지 확인

### 데이터베이스 연결 실패

- DATABASE_URL 형식 확인: `postgresql://user:password@host:port/database`
- Railway PostgreSQL 서비스가 실행 중인지 확인

## 자세한 안내

- Railway DATABASE_URL 설정: `RAILWAY_DATABASE_URL_GUIDE.md` 참고
- Apify API 문서: https://docs.apify.com/api/client/python
