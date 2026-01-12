-- Kitchen Seasonal Content POC - Complete Database Migration
-- Execute this file in Railway PostgreSQL Query tab
-- Run all migrations in order: 001, 002, 003

-- ============================================================================
-- MIGRATION 001: Initial Schema
-- ============================================================================

-- Pipeline Management
CREATE TABLE IF NOT EXISTS pipeline_runs (
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

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);

-- Raw Data Tables
CREATE TABLE IF NOT EXISTS raw_reddit_posts (
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

CREATE INDEX IF NOT EXISTS idx_raw_reddit_posts_created_utc ON raw_reddit_posts(created_utc DESC);
CREATE INDEX IF NOT EXISTS idx_raw_reddit_posts_keyword ON raw_reddit_posts(keyword);
CREATE INDEX IF NOT EXISTS idx_raw_reddit_posts_subreddit ON raw_reddit_posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_raw_reddit_posts_upvotes ON raw_reddit_posts(upvotes DESC);

CREATE TABLE IF NOT EXISTS raw_reddit_comments (
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

CREATE INDEX IF NOT EXISTS idx_raw_reddit_comments_post_id ON raw_reddit_comments(reddit_post_id);
CREATE INDEX IF NOT EXISTS idx_raw_reddit_comments_is_top ON raw_reddit_comments(is_top) WHERE is_top = TRUE;
CREATE INDEX IF NOT EXISTS idx_raw_reddit_comments_upvotes ON raw_reddit_comments(upvotes DESC);

CREATE TABLE IF NOT EXISTS raw_serp_aio (
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

CREATE INDEX IF NOT EXISTS idx_raw_serp_aio_query ON raw_serp_aio(query);
CREATE INDEX IF NOT EXISTS idx_raw_serp_aio_snapshot_at ON raw_serp_aio(snapshot_at DESC);

CREATE TABLE IF NOT EXISTS raw_gsc_queries (
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

CREATE INDEX IF NOT EXISTS idx_raw_gsc_queries_query ON raw_gsc_queries(query);
CREATE INDEX IF NOT EXISTS idx_raw_gsc_queries_date_month ON raw_gsc_queries(date_month DESC);
CREATE INDEX IF NOT EXISTS idx_raw_gsc_queries_impressions ON raw_gsc_queries(impressions DESC);

-- Analysis Tables
CREATE TABLE IF NOT EXISTS embeddings (
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

CREATE INDEX IF NOT EXISTS idx_embeddings_doc_type_id ON embeddings(doc_type, doc_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_run_id ON embeddings(created_from_run_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_json ON embeddings USING gin (embedding_json);

CREATE TABLE IF NOT EXISTS clusters (
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

CREATE INDEX IF NOT EXISTS idx_clusters_run_id ON clusters(created_from_run_id);
CREATE INDEX IF NOT EXISTS idx_clusters_noise ON clusters(noise_label) WHERE noise_label = FALSE;

CREATE TABLE IF NOT EXISTS cluster_assignments (
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

CREATE INDEX IF NOT EXISTS idx_cluster_assignments_cluster_id ON cluster_assignments(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_assignments_doc ON cluster_assignments(doc_type, doc_id);
CREATE INDEX IF NOT EXISTS idx_cluster_assignments_representative ON cluster_assignments(is_representative) 
    WHERE is_representative = TRUE;

CREATE TABLE IF NOT EXISTS cluster_timeseries (
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

CREATE INDEX IF NOT EXISTS idx_cluster_timeseries_cluster_month ON cluster_timeseries(cluster_id, month DESC);
CREATE INDEX IF NOT EXISTS idx_cluster_timeseries_month ON cluster_timeseries(month DESC);

CREATE TABLE IF NOT EXISTS topic_qa_briefs (
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

CREATE INDEX IF NOT EXISTS idx_topic_qa_briefs_cluster_id ON topic_qa_briefs(cluster_id);
CREATE INDEX IF NOT EXISTS idx_topic_qa_briefs_category ON topic_qa_briefs(category);
CREATE INDEX IF NOT EXISTS idx_topic_qa_briefs_score ON topic_qa_briefs(score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_topic_qa_briefs_run_id ON topic_qa_briefs(created_from_run_id);

-- Triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_pipeline_runs_updated_at ON pipeline_runs;
CREATE TRIGGER update_pipeline_runs_updated_at BEFORE UPDATE ON pipeline_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_raw_reddit_posts_updated_at ON raw_reddit_posts;
CREATE TRIGGER update_raw_reddit_posts_updated_at BEFORE UPDATE ON raw_reddit_posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_raw_reddit_comments_updated_at ON raw_reddit_comments;
CREATE TRIGGER update_raw_reddit_comments_updated_at BEFORE UPDATE ON raw_reddit_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_raw_serp_aio_updated_at ON raw_serp_aio;
CREATE TRIGGER update_raw_serp_aio_updated_at BEFORE UPDATE ON raw_serp_aio
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_raw_gsc_queries_updated_at ON raw_gsc_queries;
CREATE TRIGGER update_raw_gsc_queries_updated_at BEFORE UPDATE ON raw_gsc_queries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_embeddings_updated_at ON embeddings;
CREATE TRIGGER update_embeddings_updated_at BEFORE UPDATE ON embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_clusters_updated_at ON clusters;
CREATE TRIGGER update_clusters_updated_at BEFORE UPDATE ON clusters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_cluster_assignments_updated_at ON cluster_assignments;
CREATE TRIGGER update_cluster_assignments_updated_at BEFORE UPDATE ON cluster_assignments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_cluster_timeseries_updated_at ON cluster_timeseries;
CREATE TRIGGER update_cluster_timeseries_updated_at BEFORE UPDATE ON cluster_timeseries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_topic_qa_briefs_updated_at ON topic_qa_briefs;
CREATE TRIGGER update_topic_qa_briefs_updated_at BEFORE UPDATE ON topic_qa_briefs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- MIGRATION 002: Add aio_status column
-- ============================================================================

ALTER TABLE raw_serp_aio
ADD COLUMN IF NOT EXISTS aio_status VARCHAR(20) DEFAULT 'NOT_AVAILABLE';

CREATE INDEX IF NOT EXISTS idx_raw_serp_aio_status ON raw_serp_aio(aio_status);

COMMENT ON COLUMN raw_serp_aio.aio_status IS 'AI Overview availability status: AVAILABLE, NOT_AVAILABLE, ERROR';

-- ============================================================================
-- MIGRATION 003: Add insights_json column
-- ============================================================================

ALTER TABLE topic_qa_briefs
ADD COLUMN IF NOT EXISTS insights_json JSONB;

CREATE INDEX IF NOT EXISTS idx_topic_qa_briefs_insights ON topic_qa_briefs USING gin (insights_json);

COMMENT ON COLUMN topic_qa_briefs.insights_json IS 'Platform-specific insights: content_gap_analysis, execution_checklist, publishing_window, format_recommendations, evidence_strength, safety_and_claims_flags';

-- ============================================================================
-- Verification Query
-- ============================================================================

-- Run this to verify all tables were created:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
