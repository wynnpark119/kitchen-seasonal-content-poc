# 로컬에서 데이터 다운로드 및 저장 가이드

## 방법: MCP로 데이터 가져와서 JSON 저장 → 로컬에서 DB 적재

### 1단계: MCP로 데이터셋 아이템 가져오기

각 키워드의 데이터셋 ID를 사용하여 MCP 도구로 데이터를 가져옵니다.

**예시 (첫 번째 키워드)**:
```
mcp_apify_get-dataset-items(
    datasetId="Chej96NJu2xomUrg1",
    limit=10000,
    offset=0
)
```

**모든 키워드 데이터셋 ID**:
```python
COLLECTED_DATASETS = [
    {"keyword": "spring dinner ideas", "dataset_id": "Chej96NJu2xomUrg1"},
    {"keyword": "easy spring meals", "dataset_id": "hYNaDehMRGFbLd9sW"},
    {"keyword": "what to cook in spring", "dataset_id": "espep8ycOpNwjnK0c"},
    # ... 총 20개
]
```

### 2단계: JSON 파일로 저장

MCP로 가져온 데이터를 `data/` 폴더에 JSON 파일로 저장합니다.

**파일명 형식**: `{keyword}_{dataset_id}.json`
- 예: `spring_dinner_ideas_Chej96NJu2xomUrg1.json`

**저장 위치**: `kitchen-seasonal-content-poc/data/`

### 3단계: 로컬에서 DB에 적재

```bash
# 환경 변수 설정
export DATABASE_URL="postgresql://postgres:password@host:port/database"

# 스크립트 실행
python save_keywords_local.py
```

스크립트가 `data/` 폴더의 JSON 파일들을 자동으로 읽어서 DB에 저장합니다.

## 전체 워크플로우

1. **MCP로 데이터 가져오기** (AI 어시스턴트가 수행)
   - 각 키워드별로 `mcp_apify_get-dataset-items` 호출
   - 결과를 JSON 파일로 저장

2. **로컬에서 DB 적재** (로컬에서 실행)
   ```bash
   python save_keywords_local.py
   ```

3. **결과 확인**
   ```sql
   SELECT keyword, COUNT(*) FROM raw_reddit_posts GROUP BY keyword;
   ```

## 장점

- ✅ 서버 구성 불필요 (로컬에서 실행)
- ✅ 데이터 백업 가능 (JSON 파일 보관)
- ✅ 재실행 용이 (JSON 파일만 있으면 언제든 재실행)
- ✅ 디버깅 쉬움 (로컬에서 직접 확인)

## JSON 파일 구조

각 JSON 파일은 배열 형태:
```json
[
  {
    "id": "post_id",
    "title": "Post Title",
    "body": "Post content...",
    "dataType": "post",
    ...
  },
  ...
]
```

## 다음 단계

1. MCP로 20개 키워드 데이터 가져오기
2. 각각을 JSON 파일로 저장 (`data/` 폴더)
3. `save_keywords_local.py` 실행하여 DB에 적재
