# Railway Worker에서 데이터 저장 스크립트 실행하기

## 방법 1: Railway Worker 서비스에서 직접 실행 (권장)

Railway Worker 서비스에서 실행하면 내부 URL(`railway.internal`)을 사용할 수 있습니다.

### 1. Railway Worker 서비스 Variables 설정

1. Railway 대시보드 접속
2. **Worker 서비스** 선택
3. **Variables** 탭 클릭
4. 다음 변수 추가:
   - `DATABASE_URL`: `postgresql://postgres:qZIdTpBlNKudqdYmXgLJLmgQdapGXEev@postgres-tezk.railway.internal:5432/railway`
   - `APIFY_API_TOKEN`: `your-apify-token`

### 2. 스크립트를 Worker에 추가

`save_all_keywords_api.py`를 Worker 서비스에서 실행할 수 있도록 설정:

**옵션 A: Worker 서비스에서 일회성 실행**

Railway Worker 서비스의 **"Deployments"** 탭에서:
1. "Run Command" 또는 "One-off Command" 실행
2. 명령어: `python save_all_keywords_api.py`

**옵션 B: Worker main.py에 통합**

`worker/main.py`에 임시로 추가:

```python
# worker/main.py에 추가
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "save_keywords":
        # save_all_keywords_api.py의 main() 호출
        from save_all_keywords_api import main
        main()
    else:
        # 기존 main() 실행
        main()
```

그리고 Railway Worker 서비스의 시작 명령을:
```
python -m worker.main save_keywords
```

로 변경 (일회성 실행 후 원래대로 복구)

## 방법 2: 로컬에서 실행 (공개 URL 필요)

로컬에서 실행하려면 Railway PostgreSQL의 **공개 URL**이 필요합니다.

### 공개 URL 찾기

1. Railway PostgreSQL 서비스의 **Variables** 탭 확인
2. `PUBLIC_DATABASE_URL` 또는 공개 URL 찾기
3. 또는 Railway PostgreSQL 서비스의 **"Connect"** 탭에서 공개 연결 정보 확인

공개 URL 형식:
```
postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway
```

### 로컬 실행

```bash
export APIFY_API_TOKEN="your-token"
export DATABASE_URL="postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway"
python3 save_all_keywords_api.py
```

## 방법 3: Railway CLI 사용

```bash
# Railway CLI 설치
npm i -g @railway/cli

# 로그인 및 프로젝트 연결
railway login
railway link

# 환경 변수 설정 (Railway의 변수 사용)
railway run python save_all_keywords_api.py
```

## 추천 방법

**Railway Worker 서비스에서 실행하는 것을 권장합니다:**
- 내부 URL 사용 가능 (더 빠름)
- 보안상 더 안전 (내부 네트워크)
- Railway 환경과 동일한 설정
