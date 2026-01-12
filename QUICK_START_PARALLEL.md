# 빠른 시작: Railway에서 병렬 Reddit 수집

## 🚀 제일 좋은 방법: Railway Worker에서 실행

### 1단계: Railway 환경 변수 설정

Railway 콘솔 → Worker 서비스 → Variables 탭에서 추가:

```
APIFY_API_TOKEN=your-apify-api-token-here
```

(이미 DATABASE_URL은 설정되어 있을 것입니다)

### 2단계: 실행

#### 옵션 A: Railway CLI 사용 (권장)

```bash
railway run python run_parallel_collection.py
```

#### 옵션 B: Railway 콘솔에서 직접 실행

Railway 콘솔 → Worker 서비스 → Deployments → 새 Deployment 생성 시:
- Command: `python run_parallel_collection.py`

### 3단계: 모니터링

- **Railway 로그**: Worker 서비스의 로그 탭에서 진행 상황 확인
- **Apify 콘솔**: https://console.apify.com 에서 각 Run의 상태 확인

## 📊 수집 조건

- 각 키워드당 포스트: **200개**
- 댓글: 포스트당 **2개씩** (인기순)
- 정렬: **hot** (인기순)
- 검색 기간: **all** (전체 기간)
- NSFW 제외: **True**

## 📝 키워드 목록 (총 20개)

카테고리별 5개씩:
- SPRING_RECIPES: 5개
- SPRING_KITCHEN_STYLING: 5개
- REFRIGERATOR_ORGANIZATION: 5개
- VEGETABLE_PREP_HANDLING: 5개

## ✅ 장점

1. ✅ 네트워크 접근 자유로움
2. ✅ SSL 권한 문제 없음
3. ✅ 자동으로 DB에 저장
4. ✅ Railway 로그로 모니터링 가능
5. ✅ 20개 키워드 병렬 실행

## 📋 결과

실행 완료 후:
- 모든 데이터가 자동으로 PostgreSQL DB에 저장됨
- `pipeline_runs` 테이블에 실행 기록 저장
- Railway 로그에 상세 통계 출력
