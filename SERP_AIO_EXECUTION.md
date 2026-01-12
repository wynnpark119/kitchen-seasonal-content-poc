# SerpAPI AI Overview 샘플 수집 실행 가이드

## 완료된 작업

✅ `aio_status` 컬럼 추가 (마이그레이션 완료)
✅ 샘플 쿼리 4개 정의 (`config.py`)
✅ `--collect=serp_only` 옵션 추가 (`run_pipeline.py`)
✅ `collect_serp_aio.py` 수정 (샘플 쿼리 사용, aio_status 저장)
✅ `upsert_serp_aio` 함수 수정 (aio_status 파라미터 추가)

---

## 실행 커맨드

### 1. Dry-run (DB 쓰기 없이 상태 확인)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
python3 worker/run_pipeline.py --mode=collect --collect=serp_only --dry-run
```

**예상 출력:**
```
[DRY RUN] Would query SerpAPI for 'spring dinner ideas'
[DRY RUN] Would check AI Overview availability and length
...
Queries processed: 4
AVAILABLE: 0
NOT_AVAILABLE: 0
ERROR: 0
```

### 2. 실제 적재

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
SERPAPI_KEY="1180f58f3ddb13ffd66d47f742698a0a721150272742b7aa101a33a0d93963ef" \
python3 worker/run_pipeline.py --mode=collect --collect=serp_only
```

**예상 출력:**
```
Starting SERP AIO collection for 4 sample queries
Collecting SERP AIO for query: spring dinner ideas
Found AI Overview for 'spring dinner ideas' (length: 1234 chars, sources: 5)
...
SERP AIO collection completed:
  Queries processed: 4
  AVAILABLE: 2
  NOT_AVAILABLE: 2
  ERROR: 0
```

---

## 적재 검증 (psql)

### 1. 총 row 수 확인

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT COUNT(*) as total_rows FROM raw_serp_aio;"
```

**예상 결과:**
```
total_rows
-----------
         4
```

### 2. aio_status별 row 수

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

### 3. 최근 snapshot_at 기준 상위 10개 조회

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT query, aio_status, LENGTH(COALESCE(aio_text, '')) as text_length, snapshot_at FROM raw_serp_aio ORDER BY snapshot_at DESC LIMIT 10;"
```

**예상 결과:**
```
query                        | aio_status    | text_length | snapshot_at
-----------------------------+---------------+-------------+----------------------------
spring dinner ideas          | AVAILABLE     |        1234 | 2026-01-08 19:00:00+00
spring kitchen decor         | AVAILABLE     |         890 | 2026-01-08 19:00:01+00
refrigerator organization    | NOT_AVAILABLE |           0 | 2026-01-08 19:00:02+00
vegetable prep               | AVAILABLE     |         567 | 2026-01-08 19:00:03+00
```

### 4. 상세 조회 (AI Overview 텍스트 일부 확인)

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT query, aio_status, LEFT(COALESCE(aio_text, ''), 100) as text_preview, snapshot_at FROM raw_serp_aio WHERE aio_status = 'AVAILABLE' ORDER BY snapshot_at DESC;"
```

### 5. ERROR 확인 (있을 경우)

```bash
psql "postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
  -c "SELECT query, raw_json->>'error' as error_msg, snapshot_at FROM raw_serp_aio WHERE aio_status = 'ERROR';"
```

---

## 완료 조건 (Definition of Done)

### ✅ 최소 요구사항

1. **최소 4개 쿼리가 raw_serp_aio에 존재**
   ```sql
   SELECT COUNT(*) FROM raw_serp_aio;
   -- 결과: >= 4
   ```

2. **AVAILABLE/NOT_AVAILABLE 중 최소 1개 이상이 기록**
   ```sql
   SELECT aio_status, COUNT(*) 
   FROM raw_serp_aio 
   GROUP BY aio_status;
   -- 결과: AVAILABLE 또는 NOT_AVAILABLE 중 하나 이상 count >= 1
   ```

3. **ERROR는 0이어야 함**
   ```sql
   SELECT COUNT(*) FROM raw_serp_aio WHERE aio_status = 'ERROR';
   -- 결과: = 0
   ```
   
   **만약 ERROR가 1개 이상이면:**
   - 원인 로그 확인:
     ```sql
     SELECT query, raw_json->>'error' as error_msg, snapshot_at
     FROM raw_serp_aio
     WHERE aio_status = 'ERROR';
     ```
   - 재시도 가이드:
     - SerpAPI 키 확인
     - 네트워크 연결 확인
     - 전체 재실행:
       ```bash
       DATABASE_URL="..." SERPAPI_KEY="..." \
       python3 worker/run_pipeline.py --mode=collect --collect=serp_only
       ```

### ✅ 이상적 결과

- AVAILABLE: 2~4개
- NOT_AVAILABLE: 0~2개
- ERROR: 0개

### ✅ 데이터 품질 확인

- [ ] 각 row에 `query`, `aio_status`, `snapshot_at` 필수 필드 존재
- [ ] AVAILABLE인 경우 `aio_text`가 NULL이 아님
- [ ] `raw_json`에 전체 SerpAPI 응답 저장됨
- [ ] `cited_sources_json`에 출처 정보 저장됨 (AVAILABLE인 경우)

---

## 샘플 쿼리 목록

다음 4개 쿼리가 수집됩니다:

1. **SPRING_RECIPES**: "spring dinner ideas"
2. **SPRING_KITCHEN_STYLING**: "spring kitchen decor"
3. **REFRIGERATOR_ORGANIZATION**: "refrigerator organization"
4. **VEGETABLE_PREP_HANDLING**: "vegetable prep"

---

## 다음 단계

이 단계 성공 후:
- 본격 수집/분석 리포트 작성
- 전체 키워드 수집 (필요 시)
- AI Overview 내용 분석 및 인사이트 도출
