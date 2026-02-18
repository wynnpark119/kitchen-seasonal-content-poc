# Codebase Structure

**Analysis Date:** 2026-02-18

## Directory Layout

```
kitchen-seasonal-content-poc/
├── web/                          # Streamlit dashboard application
│   ├── app.py                   # Main dashboard entry point
│   ├── app_new.py               # Alternative dashboard version
│   ├── app_old.py               # Previous dashboard version (deprecated)
│   ├── db_queries.py            # Read-only database queries for dashboard
│   ├── gpt_utils.py             # GPT utility functions for dashboard
│   ├── components/              # Reusable Streamlit components
│   └── views/                   # Individual dashboard page views
│       ├── clustering_results.py
│       ├── keyword_msv_stats.py
│       ├── keyword_trends.py
│       ├── master_topics.py
│       ├── overview.py
│       ├── reddit_collection_posts.py
│       ├── reddit_collection_status.py
│       ├── topic_cloud.py
│       └── trend_explorer.py
│
├── worker/                       # Data collection and analysis pipeline
│   ├── main.py                  # Worker service entry point
│   ├── run_pipeline.py          # Pipeline orchestration with mode-based execution
│   ├── Dockerfile               # Worker service Docker image
│   ├── pipeline/                # Data processing stages
│   │   ├── db.py                # Database operations (CRUD, pooling)
│   │   ├── config.py            # Pipeline configuration (categories, model versions)
│   │   ├── logging.py           # Logger setup for pipeline
│   │   ├── models.py            # Pydantic models for type validation
│   │   ├── collect_reddit.py    # Reddit data collection via Apify
│   │   ├── collect_reddit_parallel.py  # Parallel Reddit collection
│   │   ├── collect_serp_aio.py  # Google SERP AI Overview collection
│   │   ├── collect_serp_results.py     # SERP results for cluster queries
│   │   ├── ingest_gsc.py        # Google Search Console CSV ingestion
│   │   ├── preprocess.py        # Text cleaning, deduplication, filtering
│   │   ├── process_apify_results.py    # Parse Apify output
│   │   ├── tfidf_clustering.py  # TF-IDF + K-Means clustering (4 clusters)
│   │   ├── clustering.py        # Alternative clustering implementation
│   │   ├── generate_serp_queries.py    # Generate search queries from clusters
│   │   ├── keywords.py          # Extract top keywords per cluster
│   │   ├── cluster_embedding.py # Generate cluster-level embeddings
│   │   ├── embedding.py         # Post-level embedding (deprecated)
│   │   ├── timeseries.py        # Monthly trend aggregation per cluster
│   │   ├── scoring.py           # Cluster scoring (seasonality, relevance)
│   │   ├── labeling.py          # LLM-based Q&A brief generation
│   │   ├── pruning.py           # Cluster filtering and noise removal
│   │   ├── save_mcp_results.py  # Save MCP-collected data
│   │   └── PRUNING_RULES.md     # Documentation of pruning logic
│   └── scripts/                 # Utility scripts
│       └── upload_json.py       # Upload JSON files to storage (S3/R2/GCS)
│
├── services/                     # Business logic services
│   ├── gpt_service.py           # LLM service (summaries, briefs, interpretation)
│   ├── clustering_service.py    # Cluster analysis service
│   └── serp_service.py          # SERP API wrapper
│
├── common/                       # Shared utilities and configuration
│   ├── config.py                # Centralized configuration (DB pool, models, env)
│   ├── db.py                    # SQLAlchemy engine and connection management
│   ├── openai_client.py         # Lazy-loaded OpenAI API client
│   ├── file_loader.py           # JSON file loading utilities
│   └── path_utils.py            # Path resolution helpers
│
├── migrations/                   # Database migrations (DDL)
│   ├── 001_initial_schema.sql   # Create all main tables
│   ├── 002_add_aio_status.sql   # Add SERP AIO status column
│   ├── 003_add_insights_json.sql    # Add insights_json column to briefs
│   ├── 004_add_cluster_serp_tables.sql  # Add cluster SERP query/result tables
│   ├── 005_add_topic_category_to_serp_results.sql
│   ├── 006_add_clustering_result_fields.sql
│   ├── 007_add_cluster_gpt_summaries.sql
│   ├── ALL_MIGRATIONS.sql       # Combined migration file
│   ├── run_migration.py         # Python migration runner
│   ├── run_query.py             # Query execution helper
│   └── verify_tables.py         # Table existence verification
│
├── data/                        # Local data directory (gitignore)
│   ├── master_topics_final_kr_en_RICH_WHY.json
│   ├── reddit_posts_data.json
│   ├── trends_2025.json
│   └── ...other JSON data files
│
├── tests/                       # Test and validation scripts
│   ├── check_database_data.py
│   ├── check_clustering_data.py
│   └── ...other validation scripts
│
├── scripts/                     # Root-level utility scripts (legacy)
│   └── Various collection and save scripts
│
├── .planning/                   # Planning and documentation
│   └── codebase/
│       ├── ARCHITECTURE.md      # This architecture document
│       └── STRUCTURE.md         # This structure document
│
├── .streamlit/                  # Streamlit configuration
│   └── config.toml
│
├── .claude/                     # Claude Code agent configuration
│   ├── commands/
│   ├── hooks/
│   ├── get-shit-done/
│   └── ...agent setup files
│
├── Dockerfile                   # Streamlit web service Docker image
├── worker/Dockerfile            # Worker service Docker image
├── requirements.txt             # Python dependencies
├── railway.json                 # Railway Streamlit service config
├── railway-worker.json          # Railway Worker service config
├── .env.example                 # Example environment variables
├── .gitignore                   # Git ignore rules
├── README.md                    # Project documentation (Korean)
├── SPEC.md                      # Detailed project specification
├── TASKS.md                     # Task tracking document
└── ...various documentation files
```

## Directory Purposes

**web/ (Dashboard):**
- Purpose: Interactive Streamlit dashboard for visualizing analysis results and metrics
- Key files: `app.py` (main), `db_queries.py` (data layer), `views/*` (pages), `gpt_utils.py` (LLM helpers)
- Usage: End-user facing interface; read-only from database

**worker/ (Pipeline):**
- Purpose: Orchestrate data collection, preprocessing, clustering, and analysis workflows
- Key files: `run_pipeline.py` (main entry), `pipeline/db.py` (CRUD), `pipeline/*` (stages)
- Usage: Backend processing; batch or scheduled execution

**worker/pipeline/ (Processing Stages):**
- Purpose: Individual data processing stages that can be run independently or sequentially
- Stages: collect → preprocess → cluster → analyze (keywords/embedding/timeseries) → label → score
- Entry: Via `run_pipeline.py` with `--mode` parameter

**services/ (Business Logic):**
- Purpose: Centralized service layer for complex operations (LLM calls, clustering)
- Key files: `gpt_service.py` (large, 31KB), `clustering_service.py`, `serp_service.py`
- Usage: Imported by pipeline and web modules for specific tasks

**common/ (Shared):**
- Purpose: Configuration, database, and API client management
- Key files: `config.py` (env vars), `db.py` (connection pool), `openai_client.py` (LLM)
- Usage: Imported by all modules for centralized configuration

**migrations/ (Database):**
- Purpose: Version-controlled database schema changes
- Key files: `001_initial_schema.sql` (14KB, all main tables), `ALL_MIGRATIONS.sql` (combined)
- Usage: Applied via `run_migration.py` or `run_migration_railway.sh`

**data/ (Local):**
- Purpose: Temporary storage for JSON data, master topics, results
- Contents: Master topics JSON, collected data snapshots, analysis results
- Note: Gitignored; used for local development and Docker volume mounting

## Key File Locations

**Entry Points:**
- Web: `web/app.py` - Main Streamlit dashboard (streamlit run)
- Worker: `worker/run_pipeline.py` - Pipeline orchestration (python with --mode)
- Worker Service: `worker/main.py` - Scheduled/background worker
- Database Migration: `migrations/run_migration.py` - Apply DDL migrations

**Configuration:**
- Environment: `.env` (local), Railway env vars (production)
- Database: `common/config.py` (DB_POOL_* settings), `common/db.py` (connection management)
- Pipeline: `worker/pipeline/config.py` (CATEGORIES, LLM_MODEL, thresholds)
- Streamlit: `.streamlit/config.toml` (UI settings, port, etc.)

**Database Schema:**
- Initial: `migrations/001_initial_schema.sql` (14KB with indexes)
- Updates: `migrations/002-007_*.sql` (incremental changes)
- Combined: `migrations/ALL_MIGRATIONS.sql` (single-file version)

**Data Files:**
- Master Topics: `data/master_topics_final_kr_en_RICH_WHY.json` (in Docker/data)
- Keywords: `data/keyword_msv_table.json`, `data/topic_cloud_keywords.json`
- Collection Results: `data/reddit_posts_data.json`, `clustering_results.json`

## Naming Conventions

**Files:**
- Pipeline stages: `{verb}_{noun}.py` (e.g., `collect_reddit.py`, `generate_serp_queries.py`)
- Database tables: `{prefix}_{entity}` (e.g., `raw_reddit_posts`, `cluster_assignments`, `topic_qa_briefs`)
- Configuration: `config.py` (centralized; one per major section)
- Utilities: Snake case, descriptive names (e.g., `file_loader.py`, `path_utils.py`)

**Database Tables:**
- Raw data: `raw_*` (reddit_posts, reddit_comments, serp_aio, gsc_queries)
- Processed: `preprocessed_*`, `clusters`, `cluster_assignments`
- Results: `topic_qa_briefs`, `cluster_timeseries`, `cluster_serp_*`
- Metadata: `pipeline_runs`, `cluster_gpt_summaries`

**Variables & Functions:**
- Snake case: `run_pipeline()`, `get_db_connection()`, `extract_keywords_for_cluster()`
- Class-based: PascalCase (e.g., `GPTService`, `TopicQABrief`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_BRIEFS_TO_GENERATE`, `SEASONAL_CATEGORIES`)

## Where to Add New Code

**New Pipeline Stage:**
- Primary code: `worker/pipeline/{new_stage}.py`
- Integration: Import in `worker/run_pipeline.py`, add to execution logic
- Configuration: Add settings to `worker/pipeline/config.py` if needed
- Logging: Use `setup_logger("stage_name")` from `worker/pipeline/logging.py`

**New Dashboard View:**
- Primary code: `web/views/{page_name}.py` with `render_{page_name}()` function
- Integration: Import in `web/app.py`, add to sidebar navigation
- Data layer: Query helpers in `web/db_queries.py`, import as needed
- Styling: Use existing Streamlit components, Plotly for charts

**New Service/Business Logic:**
- Primary code: `services/{feature}_service.py`
- Initialization: Follow `GPTService` pattern (lazy client loading)
- Error handling: Wrap API calls with try-except, return None on failure
- Logging: Use standard Python logging module

**New Database Table:**
- DDL: `migrations/{NNN}_description.sql` (follow sequence)
- CRUD operations: Add functions to `worker/pipeline/db.py`
- Indexes: Create indexes for foreign keys, frequently-queried columns (created_at, cluster_id)

**Test/Validation Script:**
- Location: `tests/` for permanent tests, root level for one-off scripts
- Naming: `check_*.py` or `verify_*.py` for validation, `save_*.py` for data operations
- Connection: Use `common/db.py` for database access

---

*Structure analysis: 2026-02-18*
