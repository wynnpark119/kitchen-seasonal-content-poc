# External Integrations

**Analysis Date:** 2026-02-18

## APIs & External Services

**LLM / Content Generation:**
- OpenAI - GPT-4o and GPT-4o-mini models for content summarization and master topic generation
  - SDK/Client: `openai` (1.0.0+)
  - Auth: OPENAI_API_KEY
  - Used in: `common/openai_client.py`, `services/gpt_service.py`
  - Functions: Cluster summarization, master topic generation, HS insight generation, content type classification

**Web Data Collection:**
- Apify - Reddit data scraping via Apify actors (actor IDs referenced in codebase)
  - SDK/Client: `apify-client` (1.0.0+)
  - Auth: APIFY_TOKEN (also referenced as APIFY_API_TOKEN in worker context)
  - Used in: `collect_reddit_apify_sdk.py`, `worker/main.py`
  - Functions: Reddit post/comment collection, data extraction, dataset management

- SerpAPI - Google search results and question-based keyword extraction
  - SDK/Client: `google-search-results` (2.4.2+)
  - Auth: SERPAPI_KEY
  - Used in: `scripts/run_serp_collection.py`, `worker/pipeline/collect_serp_aio.py`
  - Functions: AI Overview collection, featured snippets, search questions extraction

## Data Storage

**Databases:**
- PostgreSQL - Primary relational database for all persistent data
  - Connection: Via SQLAlchemy ORM
  - Connection strings: DATABASE_URL, RAILWAY_DATABASE_URL, POSTGRES_URL, POSTGRES_PRIVATE_URL
  - Used in: `common/db.py`, `web/db_queries.py`, data migration scripts
  - Tables: Keyword data, clustering results, Reddit posts/comments, SERP results, master topics

**Object Storage:**
- AWS S3 (or Cloudflare R2 S3-compatible) - Backup and archive storage
  - SDK/Client: `boto3` (1.28.0+)
  - Auth: AWS credentials (via environment/IAM role)
  - Used for: Data exports, JSON backups

- Google Cloud Storage (GCS) - Alternative cloud storage
  - SDK/Client: `google-cloud-storage` (2.10.0+)
  - Auth: GCS service account credentials
  - Used for: Optional data archival

**File-Based Storage:**
- Local JSON files (in `data/` directory)
  - master_topics_final_kr_en_RICH_WHY.json - Master topic configurations
  - reddit_posts_data.json - Cached Reddit collection results
  - trends_2025.json - Trend data
  - keyword_msv_table.json - Keyword mapping data
  - topic_cloud_keywords.json - Topic cloud data

## Authentication & Identity
**Auth Provider:**
- None (internal/no external auth)
- Application uses environment variable-based API key authentication for external services
- No user authentication/authorization system implemented

## CI/CD & Deployment
**Hosting:**
- Railway - Cloud application platform for both dashboard and worker services
  - Dashboard service: Streamlit app via railway.json
  - Worker service: Data pipeline via railway-worker.json
  - Deployment method: Docker image build and deployment
  - Restart policy: ON_FAILURE with max 10 retries

**Container Registry:**
- Docker Hub (implied via Railway)

## Data Flow & Collection
**Reddit Data Pipeline:**
- Apify handles data collection from Reddit actor
- Data saved to PostgreSQL via SQLAlchemy
- Clustering performed via HDBSCAN and scikit-learn
- Results displayed in Streamlit dashboard

**Google Search Data Pipeline:**
- SerpAPI fetches Google search results and AI Overview content
- Question extraction and analysis
- Data stored in PostgreSQL
- Visualized in keyword/SERP status views

**Embedding & Analysis:**
- OpenAI embeddings for text analysis (if used)
- GPT models for topic summarization and master topic generation
- No vector database (embeddings currently in-DB or ephemeral)

## Environment Configuration
**Required env vars:**
- DATABASE_URL - PostgreSQL connection string (primary)
- OPENAI_API_KEY - OpenAI API authentication
- APIFY_TOKEN - Apify SDK authentication
- SERPAPI_KEY - SerpAPI authentication

**Optional env vars:**
- ENVIRONMENT - Application environment (development/production)
- LOG_LEVEL - Logging verbosity
- PORT - Streamlit service port (default 8501)
- OPENAI_MODEL - Model override (default gpt-4o-mini)
- OPENAI_TIMEOUT - API request timeout in seconds (default 60)
- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD - Individual DB connection params (fallback if DATABASE_URL not set)

**Note:** .env file is used for local development but not tracked in git (.gitignore). See `.env.example` for template.

---
*Integration audit: 2026-02-18*
