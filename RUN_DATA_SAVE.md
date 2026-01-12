# 데이터 저장 실행 가이드

## Railway 대시보드에서 실행 (권장)

### 방법 1: Worker 서비스에서 직접 실행

1. **Railway 대시보드 접속**
   - https://railway.app 접속
   - 프로젝트 `kitchen-seasonal-content-poc` 선택

2. **Worker 서비스 선택**
   - Worker 서비스 클릭
   - "Deploy" 탭 또는 "Settings" 탭으로 이동

3. **환경 변수 확인**
   - "Variables" 탭에서 다음 변수가 설정되어 있는지 확인:
     - `DATABASE_URL` (PostgreSQL 서비스에서 자동 주입)
     - `APIFY_API_TOKEN` (수동 설정 필요)

4. **실행 방법**

   **옵션 A: Worker 모드로 실행**
   - Variables에 다음 추가:
     ```
     WORKER_MODE=save_keywords
     WORKER_ONCE=true
     ```
   - Worker 서비스를 재시작하면 자동 실행

   **옵션 B: Railway CLI로 실행** (로컬 터미널에서)
   ```bash
   cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc
   railway run python save_all_keywords_api.py
   ```

   **옵션 C: Railway 대시보드에서 직접 실행**
   - Worker 서비스 > "Deploy" 탭
   - "Run Command" 또는 "Execute" 버튼 클릭
   - 명령어 입력: `python save_all_keywords_api.py`

## 환경 변수 설정

### 필수 환경 변수

1. **DATABASE_URL**
   - PostgreSQL 서비스의 "Variables" 탭에서 복사
   - 형식: `postgresql://postgres:password@host:port/database`
   - Worker 서비스에 자동 주입되거나 수동 설정

2. **APIFY_API_TOKEN**
   - Apify 콘솔에서 발급: https://console.apify.com/
   - Settings > Integrations > API tokens
   - Worker 서비스 Variables에 추가

### 선택적 환경 변수

- `LOG_LEVEL=INFO` (기본값: INFO)
- `WORKER_ONCE=true` (한 번만 실행)

## 실행 확인

### 로그 확인 포인트

실행 시작 시:
```
✅ 데이터베이스 연결 성공
✅ Apify 클라이언트 초기화 완료
Pipeline run 생성: run_id=X
총 20개 키워드 데이터 저장 시작
```

각 키워드 처리 시:
```
[1/20] Processing: spring dinner ideas
  Dataset ID: Chej96NJu2xomUrg1
  Dataset has 889 items
  Fetched 889 items (total: 889)
  Processing 889 items...
  Batch upserted 889 posts, 0 errors
  ✅ spring dinner ideas: 889 posts, 0 comments
```

완료 시:
```
저장 완료!
  처리된 키워드: 20/20
  총 포스트: 16000
  총 댓글: 0
```

### 데이터베이스 확인

저장 완료 후 PostgreSQL에서 확인:
```sql
-- 전체 포스트 수 확인
SELECT COUNT(*) FROM raw_reddit_posts;

-- 키워드별 포스트 수 확인
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY count DESC;

-- 최근 저장된 포스트 확인
SELECT keyword, title, created_at 
FROM raw_reddit_posts 
ORDER BY created_at DESC 
LIMIT 10;
```

## 문제 해결

### 에러: "DATABASE_URL not found"
- Worker 서비스 Variables에 `DATABASE_URL` 추가
- PostgreSQL 서비스 Variables에서 복사

### 에러: "APIFY_API_TOKEN이 설정되지 않았습니다"
- Apify 콘솔에서 API Token 발급
- Worker 서비스 Variables에 추가

### 에러: "Failed to create connection pool"
- `DB_LOADING_FAILURE_ANALYSIS.md` 참고
- SSL 설정 확인
- Railway 로그에서 상세 에러 확인

### 연결 타임아웃
- Railway 네트워크 상태 확인
- PostgreSQL 서비스 상태 확인
- 재시도 (스크립트에 재시도 로직 포함)

## 예상 소요 시간

- 키워드당 약 1-2분
- 총 20개 키워드: 약 20-40분
- 네트워크 상태에 따라 변동 가능

## 저장될 데이터

- **총 키워드**: 20개
- **예상 포스트 수**: 약 16,000-18,000개
- **예상 댓글 수**: 약 0개 (현재 설정에서는 댓글 수집 안 함)
