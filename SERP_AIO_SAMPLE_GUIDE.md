# SerpAPI AI Overview 샘플 수집 가이드

## 목표
SerpAPI로 AI Overview만 샘플 수집(4개 쿼리) 후, Postgres(raw_serp_aio)에 정상 적재 검증

---

## 1. 샘플 쿼리 정의

`worker/pipeline/config.py`에 다음 4개 쿼리가 정의되어 있습니다:

```python
SERP_AIO_SAMPLE_QUERIES = {
    "SPRING_RECIPES": "spring dinner ideas",
    "SPRING_KITCHEN_STYLING": "spring kitchen decor",
    "REFRIGERATOR_ORGANIZATION": "refrigerator organization",
    "VEGETABLE_PREP_HANDLING": "vegetable prep"
}
```

각 대주제별 1개씩, 총 4개 쿼리만 수집합니다 (비용 최소화).

---

## 2. 데이터베이스 마이그레이션

`aio_status` 컬럼이 추가되었는지 확인:

```bash
# 마이그레이션 실행
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
python3 -c "
import psycopg2
import os
with open('migrations/002_add_aio_status.sql', 'r') as f:
    sql = f.read()
conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway'))
cur = conn.cursor()
cur.execute(sql)
conn.commit()
print('Migration completed')
"
```

---

## 3. 실행 커맨드

### 3.1 Dry-run (DB 쓰기 없이 상태 확인)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
python3 worker/run_pipeline.py --mode=collect --collect=serp_only --dry-run
```

**예상 출력:**
- 4개 쿼리 처리 로그
- 각 쿼리별 AI Overview 존재 여부 (AVAILABLE/NOT_AVAILABLE)
- AI Overview 텍스트 길이 (있는 경우)
- Cited sources 개수 (있는 경우)

### 3.2 실제 적재

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
SERPAPI_KEY="1180f58f3ddb13ffd66d47f742698a0a721150272742b7aa101a33a0d93963ef" \
python3 worker/run_pipeline.py --mode=collect --collect=serp_only
```

**예상 출력:**
- 4개 쿼리 처리 완료
- AVAILABLE/NOT_AVAILABLE/ERROR 통계
- DB 적재 완료 메시지

---

## 4. 적재 검증 (psql)

### 4.1 총 row 수 확인

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT COUNT(*) as total_rows FROM raw_serp_aio;"
```

**예상 결과:** `total_rows = 4` (4개 쿼리)

### 4.2 aio_status별 row 수

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT aio_status, COUNT(*) as count FROM raw_serp_aio GROUP BY aio_status ORDER BY count DESC;"
```

**예상 결과:**
```
aio_status     | count
---------------+-------
AVAILABLE      |    2
NOT_AVAILABLE  |    2
```

또는

```
aio_status     | count
---------------+-------
AVAILABLE      |    4
NOT_AVAILABLE  |    0
```

### 4.3 최근 snapshot_at 기준 상위 10개 조회

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT query, aio_status, LENGTH(aio_text) as text_length, snapshot_at FROM raw_serp_aio ORDER BY snapshot_at DESC LIMIT 10;"
```

**예상 결과:**
```
query                        | aio_status    | text_length | snapshot_at
-----------------------------+---------------+-------------+----------------------------
spring dinner ideas          | AVAILABLE     |        1234 | 2026-01-08 18:00:00+00
spring kitchen decor         | AVAILABLE     |         890 | 2026-01-08 18:00:01+00
refrigerator organization    | NOT_AVAILABLE |           0 | 2026-01-08 18:00:02+00
vegetable prep               | AVAILABLE     |         567 | 2026-01-08 18:00:03+00
```

### 4.4 상세 조회 (AI Overview 텍스트 일부 확인)

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT query, aio_status, LEFT(aio_text, 100) as text_preview, snapshot_at FROM raw_serp_aio WHERE aio_status = 'AVAILABLE' ORDER BY snapshot_at DESC;"
```

---

## 5. 완료 조건 (Definition of Done)

### ✅ 최소 요구사항
- [ ] **최소 4개 쿼리가 raw_serp_aio에 존재**
  - `SELECT COUNT(*) FROM raw_serp_aio;` → `>= 4`

- [ ] **AVAILABLE/NOT_AVAILABLE 중 최소 1개 이상이 기록**
  - `SELECT aio_status, COUNT(*) FROM raw_serp_aio GROUP BY aio_status;`
  - AVAILABLE 또는 NOT_AVAILABLE 중 하나 이상 `count >= 1`

- [ ] **ERROR는 0이어야 함**
  - `SELECT COUNT(*) FROM raw_serp_aio WHERE aio_status = 'ERROR';` → `= 0`
  - 만약 ERROR가 1개 이상이면:
    - 원인 로그 확인: `SELECT query, raw_json FROM raw_serp_aio WHERE aio_status = 'ERROR';`
    - 재시도 가이드 제시

### ✅ 이상적 결과
- AVAILABLE: 2~4개
- NOT_AVAILABLE: 0~2개
- ERROR: 0개

### ✅ 데이터 품질 확인
- [ ] 각 row에 `query`, `aio_status`, `snapshot_at` 필수 필드 존재
- [ ] AVAILABLE인 경우 `aio_text`가 NULL이 아님
- [ ] `raw_json`에 전체 SerpAPI 응답 저장됨

---

## 6. 에러 처리

### ERROR 발생 시

1. **원인 확인:**
```sql
SELECT query, raw_json->>'error' as error_msg, snapshot_at
FROM raw_serp_aio
WHERE aio_status = 'ERROR';
```

2. **재시도:**
```bash
# 특정 쿼리만 재수집하려면 collect_serp_aio.py를 수정하거나
# 전체 재실행
DATABASE_URL="..." SERPAPI_KEY="..." \
python3 worker/run_pipeline.py --mode=collect --collect=serp_only
```

3. **일반적인 에러 원인:**
- SerpAPI 키 만료/잘못됨
- API rate limit 초과
- 네트워크 오류
- 쿼리 형식 오류

---

## 7. 다음 단계

이 단계 성공 후:
- 본격 수집/분석 리포트 작성
- 전체 키워드 수집 (필요 시)
- AI Overview 내용 분석 및 인사이트 도출
