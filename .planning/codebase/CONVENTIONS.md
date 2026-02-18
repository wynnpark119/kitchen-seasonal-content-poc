# Coding Conventions

**Analysis Date:** 2026-02-18

## Naming Patterns

**Files:**
- Snake_case for all Python modules (e.g., `db.py`, `gpt_service.py`, `cluster_embedding.py`)
- Descriptive, single-responsibility names (e.g., `collect_reddit.py`, `generate_serp_queries.py`)
- Modules grouped by function: `services/` (business logic), `worker/pipeline/` (ETL), `web/` (UI), `common/` (utilities)
- Configuration files use uppercase: `.env`, `config.py`

**Functions:**
- Snake_case for all function names (e.g., `generate_cluster_summary()`, `get_connection_pool()`, `to_python_int()`)
- Prefix patterns: `get_*()` for accessors, `set_*()` for mutations, `_*()` for private functions
- Verb-first naming convention (action verbs at start): `generate_*()`, `collect_*()`, `create_*()`, `update_*()`, `run_*()`, `build_*()`, `extract_*()`, `calculate_*()`, `validate_*()`, `query_*()`, `setup_*()`, `reset_*()`, `load_*()`, `save_*()`, `ingest_*()`, `process_*()`, `generate_*()`, `classify_*()`, `truncate_*()`, `upsert_*()`, `fetch_*()`, `execute_*()`, `parse_*()`, `transform_*()`, `normalize_*()`, `retry_*()`, `timeout_*()`, `close_*()`, `yield_*()`, `handle_*()`, `prepare_*()`, `format_*()`, `map_*()`, `convert_*()`, `ensure_*()`, `assert_*()`, `is_*()` / `has_*()` for booleans, `check_*()` for validation

**Variables:**
- Snake_case for all variables: `database_url`, `top_keywords`, `pipeline_run`, `connection_pool`, `api_key`, `max_retries`, `cluster_id`, `session_local`
- Descriptive names that indicate type/purpose: `_client` (private property), `logger`, `handler`, `conn`, `db`, `pool`, `stats`, `metadata`, `params`, `config`, `service`
- Constants in UPPERCASE: `MAX_TOKENS`, `DB_POOL_MINCONN`, `DB_POOL_MAXCONN`, `API_MAX_RETRIES`, `API_BACKOFF_FACTOR`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `ISOLATION_LEVEL_AUTOCOMMIT`
- Type hints consistently used in function signatures: `-> Optional[str]`, `-> Dict[str, Any]`, `-> List[str]`, `-> bool`, `: str =`, `: int =`
- Boolean variables: `is_openai_available()`, `has_*`, `dry_run`, `override`, `autocommit`, `autoflush`

## Code Style

**Formatting:**
- Standard Python conventions (no explicit formatter configured, but follows PEP 8 patterns)
- Lines observed up to 100+ characters (no strict limit enforced)
- Indentation: 4 spaces (consistent throughout)
- String quotes: Mixed usage of single `'` and double `"` quotes (no strict preference)
- Multi-line imports formatted with parentheses

**Linting:**
- No linting tools configured (.pylintrc, .flake8, setup.cfg not present)
- Code follows implicit PEP 8 conventions
- Type hints used throughout for IDE support and code clarity

## Import Organization

**Order:**
1. Standard library imports: `os`, `sys`, `json`, `logging`, `time`, `traceback`, `threading`, `from pathlib import Path`, `from typing import Optional, List, Dict, Any`, `from datetime import datetime`, `from functools import wraps`
2. Third-party imports: `streamlit`, `pandas`, `numpy`, `openai`, `sqlalchemy`, `psycopg2`, `boto3`, `scikit-learn` (sklearn), `hdbscan`, `wordcloud`, `plotly`, `matplotlib`
3. Local/project imports: `from common.*`, `from services.*`, `from worker.pipeline.*`, `from web.*`

**Pattern:**
```python
"""Module docstring with description"""
import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

from common.config import DATABASE_URL
from services.gpt_service import GPTService
```

## Error Handling

**Patterns:**
- Explicit exception handling with specific exception types (not bare `except:`)
- Common exceptions caught with tuple grouping: `except (RateLimitError, APIConnectionError, APITimeoutError) as e:`
- Retry logic with exponential backoff: `wait_time = (API_BACKOFF_FACTOR ** attempt) + random.uniform(0, 1)`
- Broad fallback handling with comments explaining intent: `except Exception as e: # Fallback if config not available`
- Logging exceptions with `logger.exception()` for context (includes traceback)
- Silent failures with None returns in service methods: `except Exception as e: return None`
- Logger.info/warning/error used appropriately for severity levels
- Try-finally blocks for resource cleanup (database connections): `finally: db.close()`
- Guard clauses checking preconditions at function start: `if not is_openai_available(): return None`
- Environment variable fallbacks in sequential order: `os.getenv("DATABASE_URL") or os.getenv("RAILWAY_DATABASE_URL") or ...`
- Graceful degradation when optional imports missing: `try: from dotenv import load_dotenv except ImportError: ...`

## Logging

**Framework:** Python's built-in `logging` module with custom `setup_logger()` utility

**Implementation:**
- Centralized logger setup in `worker/pipeline/logging.py`
- Each module gets module-specific logger: `logger = setup_logger(__name__)` or `logger = setup_logger("module_name")`
- Standard format: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`
- Handlers write to stdout (StreamHandler)
- Log level configurable via `LOG_LEVEL` environment variable (default: "INFO")
- Logger used for:
  - Debug info: `logger.debug()`
  - Processing steps: `logger.info()`
  - Warnings: `logger.warning()` with context
  - Errors: `logger.error()` with exception details
  - Full tracebacks: `logger.exception()`
- Separators used for visual clarity: `logger.info("=" * 60)`
- Console print() statements also used alongside logging (mix observed)

## Comments

**When to Comment:**
- Module docstrings explain purpose, scope, and any special handling: `"""Database connection and helper functions\n\npsycopg2 자동 감지 및 분기 처리 포함"""`
- Function docstrings (Google-style or custom): Args, Returns, Raises sections
- Inline comments for non-obvious logic or workarounds: `# 이미 환경 변수가 설정되어 있지 않을 때만 설정`
- Comments explain "why" not "what" (code is readable enough)
- Multi-language: Mix of English and Korean comments (codebase used by Korean team)
- Complex conditions documented: Comments above try-except blocks explaining fallback intent
- Database query comments: SQL logic explained inline
- Configuration comments: Environment variable expectations documented

## Function Design

**Size:**
- Mostly 20-100 lines with some reaching 200+ for complex ETL logic
- Shorter utility functions (10-20 lines) for simple operations
- Longer functions in pipeline modules (e.g., `run_tfidf_clustering()` > 150 lines) due to complex ETL flow

**Parameters:**
- Explicit parameter lists (no excessive *args, **kwargs)
- Type hints on all parameters: `cluster_id: str`, `max_retries: int = 3`, `dry_run: bool = False`
- Optional parameters with defaults: `= None`, `= False`, `= 0`
- Complex objects passed as Dict or List with type hints: `reddit_clusters: List[Dict[str, Any]]`
- Configuration passed via module-level constants or as parameters
- Return type hints always specified: `-> Optional[str]`, `-> Dict[str, Any]`, `-> None`

## Module Design

**Exports:**
- Explicit function exports at module level (no `__all__` observed)
- Module-level configuration constants: `EMBEDDING_MODEL`, `DB_POOL_MINCONN`, etc.
- Service classes instantiated as singletons with `get_*_service()` factory functions
- Database connections created via factory functions: `get_connection_pool()`, `get_db_connection()`
- Utility functions exported directly: `setup_logger()`, `to_python_int()`, etc.
- Private functions prefixed with `_`: `_load_json()`, `_pgvector_available`, `_connection_pool`
- Database helper functions exported for reuse across modules

**Class Design:**
- Classes used for service layers (`GPTService`, `ClusteringService`)
- Classes have `__init__()` with lazy loading patterns (@property decorators)
- Single responsibility principle: `GPTService` handles OpenAI API calls, `ClusteringService` handles clustering data
- Services maintain internal state with private attributes (`_client`, `_json_data`)

---
*Convention analysis: 2026-02-18*
