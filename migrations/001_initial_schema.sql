-- Kitchen Seasonal Content POC - Initial Database Schema
-- PostgreSQL DDL
-- Version: 1.0
-- Created: 2025-01-08

-- Note: pgvector extension is not available on Railway PostgreSQL
-- Using JSONB for embedding storage instead
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Pipeline Management
-- ============================================================================

CREATE TABLE pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL, -- 'full', 'incremental', 'reddit_only', etc.
    status VARCHAR(20) NOT NULL DEFAULT 'running', -- 'running', 'completed', 'failed'
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

-- Reddit Posts (Raw)
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

-- Reddit Comments (Raw)
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

-- SERP AI Overview (Raw)
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

-- Google Search Console (Raw)
CREATE TABLE raw_gsc_queries (
    id SERIAL PRIMARY KEY,
    query VARCHAR(500) NOT NULL,
    page VARCHAR(2000),
    country VARCHAR(10) NOT NULL DEFAULT 'usa',
    device VARCHAR(20) NOT NULL DEFAULT 'desktop', -- 'desktop', 'mobile', 'tablet'
    date_month DATE NOT NULL, -- YYYY-MM-01 format for monthly aggregation
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    ctr NUMERIC(5, 4) NOT NULL DEFAULT 0, -- Click-through rate
    position NUMERIC(5, 2), -- Average position
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

-- Embeddings (using JSONB instead of pgvector)
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL, -- 'reddit_post', 'reddit_comment', etc.
    doc_id VARCHAR(100) NOT NULL, -- References the source document ID
    text_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of the text for deduplication
    embedding_json JSONB NOT NULL, -- Array of floats [0.123, 0.456, ...] for all-MiniLM-L6-v2 (384 dimensions)
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
-- GIN index for JSONB queries
CREATE INDEX idx_embeddings_json ON embeddings USING gin (embedding_json);

-- Clusters
CREATE TABLE clusters (
    cluster_id SERIAL PRIMARY KEY,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'HDBSCAN',
    params_json JSONB NOT NULL, -- HDBSCAN parameters (min_cluster_size, min_samples, etc.)
    noise_label BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE if this is a noise cluster
    size INTEGER NOT NULL DEFAULT 0, -- Number of documents in cluster
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_clusters_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_clusters_run_id ON clusters(created_from_run_id);
CREATE INDEX idx_clusters_noise ON clusters(noise_label) WHERE noise_label = FALSE;

-- Cluster Assignments (which documents belong to which cluster)
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

-- Cluster Timeseries (monthly aggregation per cluster)
CREATE TABLE cluster_timeseries (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    month DATE NOT NULL, -- YYYY-MM-01 format
    reddit_post_count INTEGER NOT NULL DEFAULT 0,
    reddit_weighted_score NUMERIC(10, 2) NOT NULL DEFAULT 0, -- Weighted by upvotes
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

-- Topic Q&A Briefs (LLM-generated content briefs)
CREATE TABLE topic_qa_briefs (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    topic_title VARCHAR(500) NOT NULL,
    primary_question TEXT NOT NULL,
    related_questions_json JSONB, -- Array of related questions
    blog_angle TEXT,
    social_angle TEXT,
    why_now_json JSONB, -- Structured why_now data
    evidence_pack_json JSONB, -- Reddit posts, GSC data, SERP AIO references
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    score NUMERIC(5, 2), -- Quality score (0-100)
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

-- Apply updated_at trigger to all tables
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

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE pipeline_runs IS 'Tracks pipeline execution runs for reproducibility';
COMMENT ON TABLE raw_reddit_posts IS 'Raw Reddit posts collected from Apify';
COMMENT ON TABLE raw_reddit_comments IS 'Raw Reddit comments (Top 3 per post)';
COMMENT ON TABLE raw_serp_aio IS 'Raw Google SERP AI Overview snapshots from SerpAPI';
COMMENT ON TABLE raw_gsc_queries IS 'Raw Google Search Console data (CSV import, last year)';
COMMENT ON TABLE embeddings IS 'Document embeddings using sentence-transformers (pgvector)';
COMMENT ON TABLE clusters IS 'HDBSCAN clustering results';
COMMENT ON TABLE cluster_assignments IS 'Document-to-cluster assignments';
COMMENT ON TABLE cluster_timeseries IS 'Monthly aggregated metrics per cluster';
COMMENT ON TABLE topic_qa_briefs IS 'LLM-generated Q&A briefs for content planning';

COMMENT ON COLUMN raw_gsc_queries.date_month IS 'YYYY-MM-01 format for monthly aggregation';
COMMENT ON COLUMN cluster_timeseries.month IS 'YYYY-MM-01 format for monthly time series';
COMMENT ON COLUMN embeddings.embedding_json IS 'Vector embedding stored as JSONB array of floats (384 dimensions for all-MiniLM-L6-v2)';
COMMENT ON COLUMN topic_qa_briefs.category IS 'One of 4 main topics: SPRING_RECIPES, SPRING_KITCHEN_STYLING, REFRIGERATOR_ORGANIZATION, VEGETABLE_PREP_HANDLING';
