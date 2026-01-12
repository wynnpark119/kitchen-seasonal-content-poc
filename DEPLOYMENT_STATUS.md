# 배포 상태 및 다음 단계

## 배포 완료 ✅

**커밋**: `965e237` - DB 적재 실패 수정사항 배포 완료

**주요 수정사항**:
1. Railway PostgreSQL SSL 설정 강화
2. 배치 처리 안전장치 추가 (크기 제한, 재시도 로직)
3. 환경 변수 읽기 순서 통일
4. 상세 에러 로깅 추가

## 배포 확인 방법

### 1. Railway 대시보드에서 확인
- Worker 서비스 로그 확인
- 다음 메시지가 보이면 정상:
  - `"Connection pool created successfully"`
  - `"Added sslmode=require to Railway database URL"` (필요시)

### 2. 데이터베이스 연결 테스트
Railway Worker 서비스에서 실행:
```bash
railway run python -c "from worker.pipeline.db import get_db_connection; conn = get_db_connection(); print('✅ 연결 성공'); conn.close()"
```

### 3. 데이터 저장 테스트
```bash
railway run python save_all_keywords_api.py
```

## 다음 단계: 데이터 저장 계속 진행

### 현재 상태
- ✅ 20개 키워드의 Apify 데이터셋 수집 완료
- ⏳ 데이터베이스 저장 필요

### 저장 방법

#### 옵션 1: Railway Worker에서 실행
```bash
# Railway Worker 서비스에서
railway run python save_all_keywords_api.py
```

#### 옵션 2: Worker 모드로 실행
Railway Worker 서비스 환경 변수 설정:
- `WORKER_MODE=save_keywords`
- `WORKER_ONCE=true`
- `APIFY_API_TOKEN=your-token`
- `DATABASE_URL=your-database-url`

#### 옵션 3: 로컬에서 실행
```bash
export APIFY_API_TOKEN="your-token"
export DATABASE_URL="your-database-url"
python3 save_all_keywords_api.py
```

## 저장될 키워드 목록 (20개)

### SPRING_RECIPES (5개)
1. spring dinner ideas
2. easy spring meals
3. what to cook in spring
4. spring meal prep
5. light spring recipes

### SPRING_KITCHEN_STYLING (5개)
6. spring kitchen decor
7. kitchen spring refresh
8. spring table setting ideas
9. how to decorate kitchen for spring
10. spring kitchen ideas

### REFRIGERATOR_ORGANIZATION (5개)
11. refrigerator organization
12. fridge organization tips
13. how to organize refrigerator
14. refrigerator storage ideas
15. fridge organization system

### VEGETABLE_PREP_HANDLING (5개)
16. vegetable prep
17. how to prep vegetables
18. vegetable storage tips
19. how to store vegetables
20. vegetable washing tips

## 예상 결과

각 키워드당 약 800-900개 포스트가 저장될 예정입니다.
총 약 16,000-18,000개 포스트가 데이터베이스에 저장됩니다.

## 모니터링

저장 진행 상황은 Railway Worker 로그에서 확인할 수 있습니다:
- `"Processing: {keyword}"`
- `"Batch upserted X posts"`
- `"✅ {keyword}: X posts, Y comments"`

저장 완료 후 데이터 확인:
```sql
SELECT keyword, COUNT(*) as count 
FROM raw_reddit_posts 
GROUP BY keyword 
ORDER BY count DESC;
```
