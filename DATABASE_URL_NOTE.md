# DATABASE_URL 주의사항

## Railway 내부 URL vs 공개 URL

Railway PostgreSQL 서비스의 Variables 탭에는 보통 **두 가지 URL**이 있습니다:

### 1. 내부 URL (Railway 서비스 간 통신용)
```
postgresql://postgres:password@postgres-tezk.railway.internal:5432/railway
```
- **용도**: Railway 서비스 간 통신 (예: Worker → PostgreSQL)
- **특징**: `railway.internal` 도메인 사용
- **로컬 접속**: ❌ 불가능 (Railway 네트워크 내부에서만 접속 가능)

### 2. 공개 URL (로컬/외부 접속용)
```
postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway
```
- **용도**: 로컬 개발, 외부 도구 접속
- **특징**: `railway.app` 도메인 사용
- **로컬 접속**: ✅ 가능

## 로컬에서 스크립트 실행 시

**공개 URL을 사용해야 합니다!**

Railway PostgreSQL 서비스의 Variables 탭에서:
- `DATABASE_URL` (공개 URL) 또는
- `PUBLIC_DATABASE_URL` 같은 이름의 변수를 찾아서 사용하세요

만약 공개 URL이 없다면:
1. Railway PostgreSQL 서비스의 **"Connect"** 또는 **"Settings"** 탭 확인
2. 공개 연결 정보 확인
3. 또는 Railway CLI 사용: `railway variables` 명령으로 확인

## Railway Worker 서비스에서 실행 시

Railway Worker 서비스의 Variables 탭에 `DATABASE_URL`을 설정하면:
- 내부 URL을 사용해도 됩니다 (Railway 네트워크 내부에서 실행되므로)
- 또는 공개 URL을 사용해도 됩니다

## 확인 방법

```bash
# 로컬에서 연결 테스트
psql "postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway"

# 또는 Python으로 테스트
python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway')
print('✅ 연결 성공')
conn.close()
"
```
