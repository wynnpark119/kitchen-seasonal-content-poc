# Label Mode 빠른 실행 가이드

## OpenAI API 키 설정

OpenAI API 키가 제공되었습니다. 실행 시 환경변수로 사용합니다.

---

## 실행 커맨드

### 1. Dry-run (테스트)

```bash
cd /Users/wynn.park/Desktop/dev/kitchen-seasonal-content-poc

DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=label --dry-run --max-briefs=3
```

### 2. 실제 실행 (상위 5개만 테스트)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=label --max-briefs=5
```

### 3. 전체 실행 (기본 20개)

```bash
DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
OPENAI_API_KEY="your-openai-api-key-here" \
python3 worker/run_pipeline.py --mode=label
```

---

## 사전 요구사항

1. **마이그레이션 실행**: `insights_json` 컬럼 추가
   ```bash
   DATABASE_URL="postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway" \
   python3 -c "
   import psycopg2
   import os
   with open('migrations/003_add_insights_json.sql', 'r') as f:
       sql = f.read()
   conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://postgres:WhNplDLWItCGNqztEpSAySUHAuFtJsCi@nozomi.proxy.rlwy.net:23515/railway'))
   cur = conn.cursor()
   cur.execute(sql)
   conn.commit()
   print('✅ Migration completed')
   "
   ```

2. **Analyze 모드 완료**: 클러스터링이 완료되어 있어야 함
   ```bash
   # 이미 완료되었다면 스킵
   DATABASE_URL="..." OPENAI_API_KEY="..." \
   python3 worker/run_pipeline.py --mode=analyze
   ```

---

## 예상 출력

```
================================================================================
MODE: LABEL - LLM-based Cluster Labeling
================================================================================
Starting brief generation (max_briefs=5)...
Calculating priority scores for X clusters
Top 5 clusters selected:
  1. Cluster 1: score=125.50, status=Emerging
  2. Cluster 2: score=98.30, status=Competitive
  ...
Generating briefs for top 5 clusters (max_briefs=5)...
Brief created for cluster 1 (score: 125.50)
Brief created for cluster 2 (score: 98.30)
...
Brief generation completed:
  Clusters processed: 5
  Briefs created: 5
Starting score calculation...
Scoring completed: 5 briefs scored
```

---

## 검증

```sql
-- Brief 생성 확인
SELECT COUNT(*) as total_briefs
FROM topic_qa_briefs
WHERE created_from_run_id = (SELECT MAX(run_id) FROM pipeline_runs WHERE run_type = 'label');

-- Insights JSON 확인
SELECT 
    cluster_id,
    topic_title,
    insights_json IS NOT NULL as has_insights
FROM topic_qa_briefs
WHERE created_from_run_id = (SELECT MAX(run_id) FROM pipeline_runs WHERE run_type = 'label')
LIMIT 5;
```

---

## 주의사항

- **API 키 보안**: 이 키는 공개 저장소에 커밋하지 마세요
- **비용**: gpt-4o-mini는 유료 모델입니다 (토큰당 과금)
- **실행 시간**: 5개 brief 기준 약 2-3분 소요
