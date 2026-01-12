# Reddit 데이터 프루닝 실행 절차

## 1. 샘플 추출

### 1.1 키워드별 샘플 추출 SQL
```sql
-- 각 키워드별 상위 10개 포스트
SELECT 
    keyword,
    reddit_post_id,
    title,
    selftext,
    subreddit,
    upvotes,
    num_comments,
    permalink,
    author
FROM raw_reddit_posts
WHERE keyword = ?
ORDER BY upvotes DESC, num_comments DESC
LIMIT 10;

-- 각 포스트의 Top 1-2 댓글
SELECT 
    rc.body,
    rc.upvotes,
    rc.author
FROM raw_reddit_comments rc
WHERE rc.reddit_post_id = ?
ORDER BY rc.upvotes DESC
LIMIT 2;
```

### 1.2 Python 실행
```python
from worker.pipeline.pruning import get_keyword_samples

keyword = "spring dinner ideas"
samples = get_keyword_samples(keyword, limit=10)
print(f"Found {len(samples)} samples for '{keyword}'")
```

---

## 2. 판정 프로세스

### 2.1 포스트 단위 판정
```python
from worker.pipeline.pruning import evaluate_post

for post in samples:
    verdict, reason = evaluate_post(post)
    print(f"{verdict}: {reason}")
    print(f"  Title: {post['title'][:60]}...")
```

### 2.2 키워드 단위 판정
```python
from worker.pipeline.pruning import evaluate_keyword

verdict, reason, stats = evaluate_keyword(keyword, samples)
print(f"Keyword: {keyword}")
print(f"Verdict: {verdict}")
print(f"Reason: {reason}")
print(f"Stats: {stats}")
```

### 2.3 전체 키워드 프루닝
```python
from worker.pipeline.pruning import prune_keywords

results = prune_keywords()

print("KEEP keywords:")
for item in results["keep"]:
    print(f"  - {item['keyword']}: {item['reason']}")

print("\nDROP keywords:")
for item in results["drop"]:
    print(f"  - {item['keyword']}: {item['reason']}")

print("\nREVIEW keywords:")
for item in results["review"]:
    print(f"  - {item['keyword']}: {item['reason']}")
```

---

## 3. 필터링 적용

### 3.1 포스트 필터링 SQL
```sql
-- 즉시 제거 조건 적용 (예시)
DELETE FROM raw_reddit_posts
WHERE 
    -- 구매/추천 패턴
    (title ILIKE '%buy%' OR selftext ILIKE '%buy%'
     OR title ILIKE '%recommend%' OR selftext ILIKE '%recommend%'
     OR title ILIKE '%worth it%' OR selftext ILIKE '%worth it%')
    OR
    -- 고장/수리 패턴
    (title ILIKE '%not cooling%' OR selftext ILIKE '%not cooling%'
     OR title ILIKE '%broken%' OR selftext ILIKE '%broken%'
     OR title ILIKE '%repair%' OR selftext ILIKE '%repair%')
    OR
    -- 오탐 패턴
    (title ILIKE '%spring break%' OR selftext ILIKE '%spring break%'
     OR title ILIKE '%spring mattress%' OR selftext ILIKE '%spring mattress%');
```

### 3.2 키워드 삭제
```sql
-- DROP 확정 키워드의 모든 포스트 삭제
DELETE FROM raw_reddit_posts
WHERE keyword IN (
    'spring recipe book',
    'refrigerator repair',
    'vegetable gardening'
    -- ... DROP 키워드 리스트
);
```

---

## 4. 결과 확인

### 4.1 최종 키워드 리스트 확인
```sql
SELECT 
    keyword,
    COUNT(*) as post_count,
    AVG(upvotes) as avg_upvotes,
    AVG(num_comments) as avg_comments
FROM raw_reddit_posts
GROUP BY keyword
ORDER BY post_count DESC;
```

### 4.2 컷 비율 확인
```python
# 프루닝 전후 비교
before_count = 1000  # 예시
after_count = 650    # 예시

cut_ratio = (before_count - after_count) / before_count
print(f"Post cut ratio: {cut_ratio:.1%}")
print(f"Target: 30-40%")
```

---

## 5. 정제 완료 조건 체크리스트

- [ ] 각 키워드별 최소 10개 이상 유효 포스트
- [ ] 오탐/노이즈 포스트 제거 완료
- [ ] 4대 주제별로 최소 1개 키워드 이상 유지
- [ ] DROP 키워드 제거 완료
- [ ] REVIEW 키워드 판정 완료
- [ ] 최종 키워드 리스트 확정
- [ ] Negative keywords 적용 완료
- [ ] 포스트 필터링 완료
- [ ] 컷 비율 목표 달성 (포스트 30-40%, 키워드 20-30%)
- [ ] `pipeline_runs`에 정제 상태 기록

---

## 6. 다음 단계

정제 완료 후:
```bash
python worker/run_pipeline.py --mode=analyze
```

이 단계에서:
- 정제된 포스트로 임베딩 생성
- HDBSCAN 클러스터링
- 클러스터별 특징어 추출
- 시계열 분석
