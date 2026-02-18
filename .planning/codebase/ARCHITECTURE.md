# Architecture

**Analysis Date:** 2026-02-18

## Pattern Overview

**Overall:** Multi-layer Microservices with Data Pipeline (Web UI + Worker Process)

**Key Characteristics:**
- Separation of concerns: Web/Dashboard layer vs. Worker/Pipeline layer
- Data-driven pipeline with stage gating (collect → preprocess → cluster → analyze → label)
- PostgreSQL-centric persistence with pooled connections
- LLM-augmented analysis (OpenAI API for embeddings, clustering interpretation, Q&A brief generation)
- Streaming/batch data collection from Reddit, Google SERP, GSC sources
- Railway-optimized deployment with containerized services (Docker)

## Layers

**Presentation Layer:**
- Purpose: Interactive Streamlit dashboard for visualizing analysis results
- Location: `/web`
- Contains: Dashboard app, view modules (views/), database query layer (db_queries.py)
- Key Entry: `web/app.py` - Main Streamlit application

**Service Layer:**
- Purpose: Business logic abstraction for GPT analysis, clustering, SERP processing
- Location: `/services`
- Contains:
  - `gpt_service.py` - LLM-based summaries, Q&A generation, cluster interpretation
  - `clustering_service.py` - Cluster analysis and processing
  - `serp_service.py` - SERP API wrapper

**Data Access Layer:**
- Purpose: Database connection pooling, query execution, ORM abstraction
- Location: `/common`, `/web/db_queries.py`, `/worker/pipeline/db.py`
- Contains:
  - `common/db.py` - SQLAlchemy engine, psycopg2 connection pooling
  - `web/db_queries.py` - Read-only SELECT queries for dashboard
  - `worker/pipeline/db.py` - Full CRUD operations for pipeline (upsert, insert, update)

**Pipeline/Worker Layer:**
- Purpose: Orchestration of data collection, processing, clustering, and analysis
- Location: `/worker`
- Contains:
  - `run_pipeline.py` - Main entry point with mode-based execution (collect, analyze, label, all)
  - `main.py` - Worker service entry point
  - `pipeline/` - Individual processing stages
  - `scripts/` - Utility scripts

**Configuration & Common Layer:**
- Purpose: Centralized configuration, environment management, OpenAI client
- Location: `/common`
- Contains:
  - `config.py` - Database pool settings, model versions, environment defaults
  - `openai_client.py` - Lazy-loaded OpenAI API client
  - `path_utils.py` - Path resolution helpers
  - `file_loader.py` - JSON data loading utilities

## Data Flow

**Collection Phase (collect mode):**
1. Reddit data collection via Apify API (`worker/pipeline/collect_reddit.py`)
2. SERP AI Overview snapshot collection (`worker/pipeline/collect_serp_aio.py`)
3. GSC CSV ingestion (`worker/pipeline/ingest_gsc.py`)
4. Raw data stored in `raw_reddit_posts`, `raw_reddit_comments`, `raw_serp_aio`, `raw_gsc_queries` tables
5. Pipeline run metadata recorded in `pipeline_runs` table

**Preprocessing Phase (first stage of analyze mode):**
1. Load raw Reddit posts from `raw_reddit_posts` table
2. Clean text, normalize whitespace, remove HTML tags (`worker/pipeline/preprocess.py`)
3. Filter deleted posts (body = "[removed]" or "[deleted]")
4. Deduplicate by SHA256 hash of analysis_text (keep highest upvote count)
5. Build safe embedding_text with token-length limits (8192 tokens)
6. Store in `preprocessed_reddit_posts` table

**Clustering Phase (second stage of analyze mode):**
1. Extract preprocessed texts
2. Vectorize using TF-IDF (scikit-learn) without embeddings (`worker/pipeline/tfidf_clustering.py`)
3. Apply K-Means clustering (4 clusters by subreddit + content signals)
4. Filter noise posts (low signal posts, clutter)
5. Store cluster assignments in `cluster_assignments` table

**Feature Extraction Phase (third stage of analyze mode):**
1. Extract top keywords per cluster using TF-IDF scores (`worker/pipeline/keywords.py`)
2. Generate SERP queries from cluster keywords (`worker/pipeline/generate_serp_queries.py`)
3. Collect SERP results for each generated query (`worker/pipeline/collect_serp_results.py`)
4. Generate cluster-level embeddings (group-level not post-level) (`worker/pipeline/cluster_embedding.py`)
5. Calculate timeseries trends per cluster (`worker/pipeline/timeseries.py`)
6. Calculate topic scores (seasonality, relevance, engagement) (`worker/pipeline/scoring.py`)

**Labeling Phase (label mode):**
1. Rank clusters by score
2. For each top cluster, call LLM with:
   - Representative posts (3-5 samples)
   - Top keywords (10-15)
   - Trend data (6 months)
   - GSC summary (if available)
   - SERP AIO summary (if available)
3. LLM generates Q&A briefs with insights fields
4. Store in `topic_qa_briefs` table with `insights_json`

**Dashboard Query Phase (web layer):**
1. Dashboard views query aggregated data from:
   - `topic_qa_briefs` (master topics with briefs)
   - `clusters` (cluster metadata)
   - `raw_reddit_posts` (post-level data)
   - `cluster_serp_results` (SERP results per cluster)
   - `raw_gsc_queries` (search console queries)
2. Cache queries using Streamlit session state
3. Render interactive visualizations (Plotly, word clouds, tables)

## Key Abstractions

**Pipeline Run (run_id):**
- Purpose: Idempotent execution tracking and reproducibility
- Examples: `pipeline_runs` table, `run_pipeline.py --mode={collect,analyze,label,all}`
- Usage: Each run gets unique run_id; upsert operations use run_id as key to prevent duplicates

**Cluster (cluster_id):**
- Purpose: Grouping of thematically related Reddit posts
- Examples: `clusters` table, `cluster_assignments` table
- Usage: Central entity linking posts, keywords, SERP queries, timeseries data, Q&A briefs

**Topic Q&A Brief (topic_qa_brief_id):**
- Purpose: LLM-generated interpretation of a cluster with insights
- Examples: `topic_qa_briefs` table with `insights_json` fields
- Usage: Final output for dashboard; includes content_gap_analysis, execution_checklist, format_recommendations

**Cluster SERP Query:**
- Purpose: Search queries derived from cluster keywords for market validation
- Examples: `cluster_serp_queries` table, `cluster_serp_results` table
- Usage: Evidence gathering for cluster relevance and market demand

**Timeseries Aggregation:**
- Purpose: Monthly trend tracking per cluster (post count, weighted engagement score)
- Examples: `cluster_timeseries` table
- Usage: Seasonality detection, trend status calculation

## Entry Points

**Web (Streamlit Dashboard):**
- Location: `web/app.py`
- Triggers: `streamlit run web/app.py` or Railway HTTP route
- Flow: Loads views from `web/views/*.py`, queries DB via `web/db_queries.py`, renders interactive dashboard

**Worker (Data Pipeline):**
- Location: `worker/run_pipeline.py`
- Triggers: `python worker/run_pipeline.py --mode={collect,analyze,label,all}` or `python -m worker.main`
- Flow:
  - Collect mode: Reddit + SERP collection
  - Analyze mode: Preprocess + cluster + feature extraction + timeseries + scoring
  - Label mode: LLM-based Q&A brief generation
  - All mode: Execute all stages sequentially

**Migration/Setup:**
- Location: `migrations/run_migration.py`
- Triggers: `python migrations/run_migration.py`
- Flow: Applies DDL migrations to create/update database schema

## Error Handling

**Strategy:** Multi-layer error recovery

1. **Database Layer** (`worker/pipeline/db.py`):
   - Connection pooling with acquire timeout (10s default)
   - Retry logic on transient failures
   - Pool fallback to direct connection if pool exhausted
   - Statement timeouts (60s default)

2. **Pipeline Layer**:
   - Try-except blocks per processing stage
   - Dry-run mode for testing (`--dry-run` flag)
   - Max error threshold (stop after N consecutive failures)
   - Failed row logging to JSON file (`failed_rows_{job_id}.json`)

3. **API Layer**:
   - OpenAI API error handling (rate limit, auth, timeout)
   - Retry with exponential backoff
   - Fallback to cached summaries if generation fails

4. **Logging**:
   - Centralized logger setup (`worker/pipeline/logging.py`)
   - Stage-specific loggers (preprocess, clustering, labeling)
   - Progress logging every 100 records or 10 seconds

## Cross-Cutting Concerns

**Logging:**
- Implementation: `worker/pipeline/logging.py` setup_logger() - returns Python logger
- Approach: INFO level for pipeline milestones, DEBUG for detailed steps
- Format: Timestamp, logger name, level, message
- Output: Console stream (Railway-compatible)

**Validation:**
- Implementation: Pydantic models (`worker/pipeline/models.py`)
- Approach: Type checking on cluster data, timeseries records
- Constraints: Non-null fields (cluster_id, run_id), valid timestamps, foreign key checks

**Configuration Management:**
- Implementation: `common/config.py`, `.env` file, environment variables
- Approach: Environment-first (Railway env vars override .env file)
- Keys: DATABASE_URL, OPENAI_API_KEY, APIFY_TOKEN, SERPAPI_KEY

**Caching:**
- Implementation: Streamlit session state (`web/app.py`)
- Approach: Cache query results during dashboard session
- TTL: Session-based (cleared on browser refresh)

**Idempotency:**
- Implementation: Upsert operations with unique key constraints
- Approach: INSERT ON CONFLICT DO UPDATE (PostgreSQL)
- Keys: (run_id, cluster_id), (reddit_post_id), (cluster_id, query)

---

*Architecture analysis: 2026-02-18*
