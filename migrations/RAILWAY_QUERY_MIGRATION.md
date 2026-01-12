# Railway Query 탭에서 마이그레이션 실행 가이드

## 실행 순서

Railway PostgreSQL 서비스의 **"Query"** 탭에서 다음 순서로 실행하세요.

---

## 1단계: 초기 스키마 생성 (001_initial_schema.sql)

### 실행 방법
1. Railway 대시보드 → PostgreSQL 서비스 (`Postgres-tezK`) 클릭
2. **"Query"** 탭 클릭
3. 아래 SQL 전체를 복사하여 붙여넣기
4. **"Run"** 또는 **"Execute"** 클릭

### SQL 내용
```sql
-- Kitchen Seasonal Content POC - Initial Database Schema
-- PostgreSQL DDL
-- Version: 1.0

-- ============================================================================
-- Pipeline Management
-- ============================================================================

CREATE TABLE pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);

-- ============================================================================
-- Raw Data Tables
-- ============================================================================

CREATE TABLE raw_reddit_posts (
    reddit_post_id VARCHAR(50) PRIMARY KEY,
    subreddit VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    author VARCHAR(100),
    created_utc BIGINT NOT NULL,
    upvotes INTEGER NOT NULL DEFAULT 0,
    num_comments INTEGER NOT NULL DEFAULT 0,
    permalink TEXT,
    url TEXT,
    keyword VARCHAR(200) NOT NULL,
    raw_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_reddit_post_id UNIQUE (reddit_post_id)
);

CREATE INDEX idx_raw_reddit_posts_created_utc ON raw_reddit_posts(created_utc DESC);
CREATE INDEX idx_raw_reddit_posts_keyword ON raw_reddit_posts(keyword);
CREATE INDEX idx_raw_reddit_posts_subreddit ON raw_reddit_posts(subreddit);
CREATE INDEX idx_raw_reddit_posts_upvotes ON raw_reddit_posts(upvotes DESC);

CREATE TABLE raw_reddit_comments (
    reddit_comment_id VARCHAR(50) PRIMARY KEY,
    reddit_post_id VARCHAR(50) NOT NULL,
    author VARCHAR(100),
    body TEXT NOT NULL,
    created_utc BIGINT NOT NULL,
    upvotes INTEGER NOT NULL DEFAULT 0,
    is_top BOOLEAN NOT NULL DEFAULT FALSE,
    raw_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_reddit_comment_id UNIQUE (reddit_comment_id),
    CONSTRAINT fk_reddit_comment_post FOREIGN KEY (reddit_post_id) 
        REFERENCES raw_reddit_posts(reddit_post_id) ON DELETE CASCADE
);

CREATE INDEX idx_raw_reddit_comments_post_id ON raw_reddit_comments(reddit_post_id);
CREATE INDEX idx_raw_reddit_comments_is_top ON raw_reddit_comments(is_top) WHERE is_top = TRUE;
CREATE INDEX idx_raw_reddit_comments_upvotes ON raw_reddit_comments(upvotes DESC);

CREATE TABLE raw_serp_aio (
    id SERIAL PRIMARY KEY,
    query VARCHAR(500) NOT NULL,
    locale VARCHAR(10) NOT NULL DEFAULT 'en-US',
    snapshot_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id INTEGER,
    aio_text TEXT,
    cited_sources_json JSONB,
    raw_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_serp_aio_query_snapshot UNIQUE (query, snapshot_at),
    CONSTRAINT fk_serp_aio_run FOREIGN KEY (run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE SET NULL
);

CREATE INDEX idx_raw_serp_aio_query ON raw_serp_aio(query);
CREATE INDEX idx_raw_serp_aio_snapshot_at ON raw_serp_aio(snapshot_at DESC);

CREATE TABLE raw_gsc_queries (
    id SERIAL PRIMARY KEY,
    query VARCHAR(500) NOT NULL,
    page VARCHAR(2000),
    country VARCHAR(10) NOT NULL DEFAULT 'usa',
    device VARCHAR(20) NOT NULL DEFAULT 'desktop',
    date_month DATE NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    ctr NUMERIC(5, 4) NOT NULL DEFAULT 0,
    position NUMERIC(5, 2),
    raw_row_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_gsc_query_month UNIQUE (query, page, country, device, date_month)
);

CREATE INDEX idx_raw_gsc_queries_query ON raw_gsc_queries(query);
CREATE INDEX idx_raw_gsc_queries_date_month ON raw_gsc_queries(date_month DESC);
CREATE INDEX idx_raw_gsc_queries_impressions ON raw_gsc_queries(impressions DESC);

-- ============================================================================
-- Analysis Tables
-- ============================================================================

CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,
    doc_id VARCHAR(100) NOT NULL,
    text_hash VARCHAR(64) NOT NULL,
    embedding_json JSONB NOT NULL,
    model_name VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    dim INTEGER NOT NULL DEFAULT 384,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_embeddings_doc_run UNIQUE (doc_type, doc_id, created_from_run_id),
    CONSTRAINT fk_embeddings_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_embeddings_doc_type_id ON embeddings(doc_type, doc_id);
CREATE INDEX idx_embeddings_run_id ON embeddings(created_from_run_id);
CREATE INDEX idx_embeddings_json ON embeddings USING gin (embedding_json);

CREATE TABLE clusters (
    cluster_id SERIAL PRIMARY KEY,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'HDBSCAN',
    params_json JSONB NOT NULL,
    noise_label BOOLEAN NOT NULL DEFAULT FALSE,
    size INTEGER NOT NULL DEFAULT 0,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_clusters_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_clusters_run_id ON clusters(created_from_run_id);
CREATE INDEX idx_clusters_noise ON clusters(noise_label) WHERE noise_label = FALSE;

CREATE TABLE cluster_assignments (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    doc_id VARCHAR(100) NOT NULL,
    distance_to_centroid NUMERIC(10, 6),
    is_representative BOOLEAN NOT NULL DEFAULT FALSE,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_cluster_assignments_doc_run UNIQUE (doc_type, doc_id, created_from_run_id),
    CONSTRAINT fk_cluster_assignments_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT fk_cluster_assignments_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_cluster_assignments_cluster_id ON cluster_assignments(cluster_id);
CREATE INDEX idx_cluster_assignments_doc ON cluster_assignments(doc_type, doc_id);
CREATE INDEX idx_cluster_assignments_representative ON cluster_assignments(is_representative) 
    WHERE is_representative = TRUE;

CREATE TABLE cluster_timeseries (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    month DATE NOT NULL,
    reddit_post_count INTEGER NOT NULL DEFAULT 0,
    reddit_weighted_score NUMERIC(10, 2) NOT NULL DEFAULT 0,
    gsc_impressions INTEGER NOT NULL DEFAULT 0,
    gsc_clicks INTEGER NOT NULL DEFAULT 0,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_cluster_timeseries_month UNIQUE (cluster_id, month, created_from_run_id),
    CONSTRAINT fk_cluster_timeseries_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT fk_cluster_timeseries_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_cluster_timeseries_cluster_month ON cluster_timeseries(cluster_id, month DESC);
CREATE INDEX idx_cluster_timeseries_month ON cluster_timeseries(month DESC);

CREATE TABLE topic_qa_briefs (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    topic_title VARCHAR(500) NOT NULL,
    primary_question TEXT NOT NULL,
    related_questions_json JSONB,
    blog_angle TEXT,
    social_angle TEXT,
    why_now_json JSONB,
    evidence_pack_json JSONB,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    score NUMERIC(5, 2),
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_topic_qa_briefs_cluster_model UNIQUE (cluster_id, model_version),
    CONSTRAINT fk_topic_qa_briefs_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT fk_topic_qa_briefs_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    CONSTRAINT chk_category CHECK (category IN (
        'SPRING_RECIPES',
        'SPRING_KITCHEN_STYLING',
        'REFRIGERATOR_ORGANIZATION',
        'VEGETABLE_PREP_HANDLING'
    ))
);

CREATE INDEX idx_topic_qa_briefs_cluster_id ON topic_qa_briefs(cluster_id);
CREATE INDEX idx_topic_qa_briefs_category ON topic_qa_briefs(category);
CREATE INDEX idx_topic_qa_briefs_score ON topic_qa_briefs(score DESC NULLS LAST);
CREATE INDEX idx_topic_qa_briefs_run_id ON topic_qa_briefs(created_from_run_id);

-- ============================================================================
-- Triggers for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_pipeline_runs_updated_at BEFORE UPDATE ON pipeline_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_raw_reddit_posts_updated_at BEFORE UPDATE ON raw_reddit_posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_raw_reddit_comments_updated_at BEFORE UPDATE ON raw_reddit_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_raw_serp_aio_updated_at BEFORE UPDATE ON raw_serp_aio
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_raw_gsc_queries_updated_at BEFORE UPDATE ON raw_gsc_queries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_embeddings_updated_at BEFORE UPDATE ON embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clusters_updated_at BEFORE UPDATE ON clusters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cluster_assignments_updated_at BEFORE UPDATE ON cluster_assignments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cluster_timeseries_updated_at BEFORE UPDATE ON cluster_timeseries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_topic_qa_briefs_updated_at BEFORE UPDATE ON topic_qa_briefs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## 2단계: aio_status 컬럼 추가 (002_add_aio_status.sql)

### 실행 방법
1. 동일한 Query 탭에서
2. 아래 SQL 복사하여 붙여넣기
3. **"Run"** 클릭

### SQL 내용
```sql
-- Add aio_status column to raw_serp_aio table

ALTER TABLE raw_serp_aio
ADD COLUMN IF NOT EXISTS aio_status VARCHAR(20) DEFAULT 'NOT_AVAILABLE';

CREATE INDEX IF NOT EXISTS idx_raw_serp_aio_status ON raw_serp_aio(aio_status);

COMMENT ON COLUMN raw_serp_aio.aio_status IS 'AI Overview availability status: AVAILABLE, NOT_AVAILABLE, ERROR';
```

---

## 3단계: insights_json 컬럼 추가 (003_add_insights_json.sql)

### 실행 방법
1. 동일한 Query 탭에서
2. 아래 SQL 복사하여 붙여넣기
3. **"Run"** 클릭

### SQL 내용
```sql
-- Add insights_json column to topic_qa_briefs table

ALTER TABLE topic_qa_briefs
ADD COLUMN IF NOT EXISTS insights_json JSONB;

CREATE INDEX IF NOT EXISTS idx_topic_qa_briefs_insights ON topic_qa_briefs USING gin (insights_json);

COMMENT ON COLUMN topic_qa_briefs.insights_json IS 'Platform-specific insights: content_gap_analysis, execution_checklist, publishing_window, format_recommendations, evidence_strength, safety_and_claims_flags';
```

---

## 완료 확인

모든 마이그레이션 실행 후, 테이블 생성 확인:

```sql
-- 테이블 목록 확인
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

예상되는 테이블 (10개):
- pipeline_runs
- raw_reddit_posts
- raw_reddit_comments
- raw_serp_aio
- raw_gsc_queries
- embeddings
- clusters
- cluster_assignments
- cluster_timeseries
- topic_qa_briefs

---

## 다음 단계

마이그레이션 완료 후:
1. Streamlit 서비스에 DATABASE_URL 설정 확인
2. Streamlit 서비스 재배포 확인
3. 대시보드 접속 테스트
