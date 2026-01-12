-- Migration: Add cluster SERP query and result tables
-- Version: 4.0
-- Created: 2025-01-09

-- ============================================================================
-- Cluster SERP Queries
-- ============================================================================

CREATE TABLE IF NOT EXISTS cluster_serp_queries (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    query_type VARCHAR(50), -- 'info_search', 'problem', 'comparison', 'case_study', 'trend'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cluster_serp_queries_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT uk_cluster_query UNIQUE (cluster_id, query)
);

CREATE INDEX IF NOT EXISTS idx_cluster_serp_queries_cluster_id ON cluster_serp_queries(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_serp_queries_query_type ON cluster_serp_queries(query_type);

-- ============================================================================
-- SERP Results
-- ============================================================================

CREATE TABLE IF NOT EXISTS serp_results (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    source VARCHAR(255), -- 도메인
    position INTEGER, -- 검색 결과 순위
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_serp_results_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT uk_serp_result_url_query UNIQUE (url, query)
);

CREATE INDEX IF NOT EXISTS idx_serp_results_cluster_id ON serp_results(cluster_id);
CREATE INDEX IF NOT EXISTS idx_serp_results_query ON serp_results(query);
CREATE INDEX IF NOT EXISTS idx_serp_results_source ON serp_results(source);
CREATE INDEX IF NOT EXISTS idx_serp_results_fetched_at ON serp_results(fetched_at DESC);

-- ============================================================================
-- Cluster Embeddings
-- ============================================================================

CREATE TABLE IF NOT EXISTS cluster_embeddings (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    embedding_json JSONB NOT NULL,
    model_name VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-large',
    dim INTEGER NOT NULL DEFAULT 3072,
    created_from_run_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_cluster_embedding_run UNIQUE (cluster_id, created_from_run_id),
    CONSTRAINT fk_cluster_embeddings_cluster FOREIGN KEY (cluster_id) 
        REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    CONSTRAINT fk_cluster_embeddings_run FOREIGN KEY (created_from_run_id) 
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cluster_embeddings_cluster_id ON cluster_embeddings(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_embeddings_run_id ON cluster_embeddings(created_from_run_id);
CREATE INDEX IF NOT EXISTS idx_cluster_embeddings_json ON cluster_embeddings USING gin (embedding_json);

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE cluster_serp_queries IS 'SERP search queries generated for each cluster';
COMMENT ON TABLE serp_results IS 'Google search results collected for cluster queries';
COMMENT ON TABLE cluster_embeddings IS 'Embeddings for cluster summaries only (not post-level)';

COMMENT ON COLUMN cluster_serp_queries.query_type IS 'Type of query: info_search, problem, comparison, case_study, trend';
COMMENT ON COLUMN serp_results.source IS 'Domain name extracted from URL';
COMMENT ON COLUMN serp_results.position IS 'Search result ranking position';
