# Technology Stack

**Analysis Date:** 2026-02-18

## Languages
**Primary:**
- Python 3.11 - Full application stack (backend API, data pipeline, frontend)

## Runtime
**Environment:**
- Python 3.11-slim (containerized via Docker)
- OS: Linux (Alpine slim variant)

**Package Manager:**
- pip
- Lockfile: requirements.txt (present at `/home/user/kitchen-seasonal-content-poc/requirements.txt`)

## Frameworks
**Core:**
- Streamlit 1.28.0+ - Web dashboard frontend (interactive UI)
- SQLAlchemy 2.0.0+ - ORM for database abstraction and query building
- FastAPI (implied by worker pipeline structure) - Backend API framework

**Testing:**
- pytest (implied via test directory structure at `tests/`)

**Build/Dev:**
- Docker - Containerization (Dockerfile at root and worker/)
- Railway - Cloud deployment platform (railway.json configuration)

## Key Dependencies
**Critical:**
- `psycopg2-binary 2.9.9+` - PostgreSQL database driver (core database connectivity)
- `pandas 2.0.0+` - Data processing and manipulation
- `numpy 1.24.0+` - Numerical computing
- `sqlalchemy 2.0.0+` - Database abstraction and ORM
- `openai 1.0.0+` - OpenAI API for GPT models (content generation, embeddings)
- `apify-client 1.0.0+` - Apify actor SDK for Reddit data collection
- `google-search-results 2.4.2+` - SerpAPI client for Google search results
- `scikit-learn 1.3.0+` - Machine learning (TF-IDF, utilities)
- `hdbscan 0.8.33+` - HDBSCAN clustering algorithm
- `plotly 5.17.0+` - Interactive visualizations
- `boto3 1.28.0+` - AWS S3 and Cloudflare R2 (S3-compatible) object storage
- `google-cloud-storage 2.10.0+` - Google Cloud Storage integration

**Utilities:**
- `python-dotenv 1.0.0+` - Environment variable management from .env files
- `pydantic 2.0.0+` - Data validation and settings management
- `pydantic-settings 2.0.0+` - Environment-based configuration
- `tiktoken 0.5.0+` - OpenAI token counting
- `wordcloud 1.9.0+` - Word cloud visualization
- `matplotlib 3.7.0+` - Plotting and visualization

## Configuration
**Environment:**
- `.env` file for local development (example template at `.env.example`)
- Railway environment variables for production deployment
- Supports multiple DATABASE_URL environment variable names (DATABASE_URL, RAILWAY_DATABASE_URL, POSTGRES_URL, POSTGRES_PRIVATE_URL)

**Build:**
- `Dockerfile` - Main application container (Streamlit dashboard)
- `worker/Dockerfile` - Worker service container (data pipeline)
- `railway.json` - Railway deployment configuration (builder: DOCKERFILE, startCommand: bash start_streamlit.sh)
- `railway-worker.json` - Worker service deployment config
- `.streamlit/config.toml` - Streamlit configuration (headless mode, CORS, stats gathering disabled)

## Platform Requirements
**Development:**
- Python 3.11+
- pip package manager
- Docker (for containerized development)
- PostgreSQL database (connection string via environment variable)

**Production:**
- Docker runtime
- Railway platform (cloud deployment)
- PostgreSQL database (Railway PostgreSQL or external)
- Environment variables: DATABASE_URL, OPENAI_API_KEY, APIFY_TOKEN, SERPAPI_KEY
- Object storage (AWS S3, Cloudflare R2, or Google Cloud Storage)

---
*Stack analysis: 2026-02-18*
