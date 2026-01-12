-- Railway 데이터베이스 상태 확인 쿼리
-- Railway PostgreSQL Query 탭에서 실행하여 현재 상태 확인

-- 1. 테이블 목록 확인
SELECT 
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 2. 각 테이블의 데이터 개수 확인 (테이블이 있는 경우)
SELECT 
    'pipeline_runs' as table_name, 
    COUNT(*) as row_count 
FROM pipeline_runs
UNION ALL
SELECT 'raw_reddit_posts', COUNT(*) FROM raw_reddit_posts
UNION ALL
SELECT 'raw_reddit_comments', COUNT(*) FROM raw_reddit_comments
UNION ALL
SELECT 'raw_serp_aio', COUNT(*) FROM raw_serp_aio
UNION ALL
SELECT 'raw_gsc_queries', COUNT(*) FROM raw_gsc_queries
UNION ALL
SELECT 'embeddings', COUNT(*) FROM embeddings
UNION ALL
SELECT 'clusters', COUNT(*) FROM clusters
UNION ALL
SELECT 'cluster_assignments', COUNT(*) FROM cluster_assignments
UNION ALL
SELECT 'cluster_timeseries', COUNT(*) FROM cluster_timeseries
UNION ALL
SELECT 'topic_qa_briefs', COUNT(*) FROM topic_qa_briefs;

-- 3. 컬럼 구조 확인 (특정 테이블)
-- raw_serp_aio 테이블에 aio_status 컬럼이 있는지 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'raw_serp_aio'
ORDER BY ordinal_position;

-- topic_qa_briefs 테이블에 insights_json 컬럼이 있는지 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'topic_qa_briefs'
ORDER BY ordinal_position;
