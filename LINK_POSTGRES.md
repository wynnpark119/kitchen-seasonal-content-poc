# PostgreSQL 서비스 연결 가이드

## 현재 상태
- ✅ PostgreSQL 서비스 생성 완료: `Postgres-tezK`
- ❌ Streamlit 서비스에 `DATABASE_URL` 환경 변수가 설정되지 않음

## 해결 방법

### 방법 1: Railway 웹 대시보드에서 연결 (권장)

1. [Railway Dashboard](https://railway.app) 접속
2. 프로젝트 `kitchen-seasonal-content-poc` 선택
3. **Streamlit 서비스** 클릭
4. **"Variables"** 탭 클릭
5. **"New Variable"** 또는 **"Connect"** 버튼 클릭
6. **PostgreSQL 서비스 (Postgres-tezK)** 선택
7. `DATABASE_URL` 환경 변수가 자동으로 추가됨

### 방법 2: Railway CLI로 연결

PostgreSQL 서비스의 DATABASE_URL을 확인하고 Streamlit 서비스에 설정:

```bash
# PostgreSQL 서비스의 DATABASE_URL 확인
railway variables --service postgres-tezk

# 또는 서비스 이름이 다를 수 있으므로 확인
railway service
```

그 다음 Streamlit 서비스에 DATABASE_URL 설정:
```bash
# PostgreSQL 서비스의 DATABASE_URL을 복사하여
railway variables set DATABASE_URL="postgresql://..." --service streamlit
```

---

## 확인 방법

### DATABASE_URL 설정 확인
```bash
railway variables --service streamlit | grep DATABASE_URL
```

### 마이그레이션 실행
DATABASE_URL이 설정되면:
```bash
# DATABASE_URL 환경 변수 설정
export DATABASE_URL=$(railway variables --service streamlit | grep DATABASE_URL | awk '{print $3}')

# 마이그레이션 실행
python migrations/run_migration.py
```

---

## 다음 단계

1. ✅ PostgreSQL 서비스 생성 완료
2. ⏳ Streamlit 서비스에 DATABASE_URL 연결
3. ⏳ 마이그레이션 실행
4. ⏳ Streamlit 서비스 재배포 확인
5. ⏳ 대시보드 접속 테스트
