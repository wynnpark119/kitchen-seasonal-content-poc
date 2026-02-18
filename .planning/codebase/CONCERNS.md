# Codebase Concerns

**Analysis Date:** 2026-02-18

## Tech Debt

### Script Proliferation (Collection & Save Scripts)
**Issue:** Massive duplication of collection and data-saving scripts with minimal variations between them
- Files: `collect_*.py` (44 scripts) and `save_*.py` (30+ scripts) at project root
- Examples: `save_all_20_keywords.py`, `save_all_20_keywords_railway.py`, `save_all_22_runs.py`, `collect_reddit_all.py`, `collect_reddit_batch.py`, `collect_parallel_apify_client.py` (JS and PY versions)
- Impact:
  - Maintenance nightmare: bugs must be fixed in multiple places
  - ~800+ lines of redundant/near-duplicate code scattered across root
  - Difficult to identify canonical versions
  - Unclear which script to use for which purpose
- Fix approach:
  - Consolidate into unified collection/save CLI with configurable modes
  - Create `worker/cli/` module with argument-driven execution
  - Implement DRY principle for data collection patterns

### Deprecated Code Still Present
**Issue:** Post-level embedding code is marked `DEPRECATED` but remains in codebase
- Files: `worker/run_pipeline.py` (line 62-64), `worker/pipeline/embedding.py`
- Impact: Code confusion, maintenance burden, unused imports still imported
- Fix approach:
  - Remove deprecated embedding.py completely
  - Keep only cluster-level embedding pipeline (`worker/pipeline/cluster_embedding.py`)
  - Document migration path clearly in SPEC.md

### Multiple App Entry Points (Web)
**Issue:** Three different Streamlit app entry points without clear purpose/status
- Files: `web/app.py`, `web/app_old.py`, `web/app_new.py`
- Impact: Confusion about which is canonical; code maintenance across versions
- Fix approach:
  - Document which is active (appears to be `web/app.py`)
  - Delete `web/app_old.py` and `web/app_new.py` or move to archive/
  - Consolidate all active view logic into single app structure

### Database Configuration Scattered
**Issue:** Database connection logic duplicated across multiple files with inconsistent handling
- Files: `common/db.py`, `common/config.py`, `web/db_queries.py`, `worker/pipeline/db.py`
- Impact:
  - Multiple conflicting implementations of URL resolution (6-line pattern repeated 4+ times)
  - Railway-specific SSL handling exists in 3+ places
  - Connection pool config management unclear
- Fix approach:
  - Single source of truth for DB initialization
  - Create `common/database.py` with pooling & SSL logic
  - Remove duplication from web/db_queries.py and worker/pipeline/db.py

### Manual .env File Reading
**Issue:** Every module manually parses `.env` files as fallback when dotenv not available
- Files: `common/config.py`, `common/db.py`, `common/openai_client.py`, `worker/pipeline/db.py`, `web/app.py`
- Impact:
  - Maintenance burden (5 implementations of same logic)
  - Risk of inconsistent parsing (quote handling, encoding)
  - 150+ lines of duplicate code
- Fix approach:
  - Create `common/env_loader.py` with single, tested implementation
  - All modules import from there

---

## Known Bugs

### Bare Exception Handlers Hide Errors
**Issue:** 28 bare `except:` clauses silently swallow all exceptions including KeyboardInterrupt
- Files: `services/clustering_service.py` (2x), `scripts/` (7+ files), `web/db_queries.py` (5+), and others
- Symptoms:
  - Errors silently fail without logging/visibility
  - Difficult to debug production issues
  - Connection leaks possible (connections not properly returned on error)
- Trigger: Any error in try block silently passes with no indication
- Example: `services/clustering_service.py:101` - bare except on DB fallback
- Fix approach:
  - Replace all `except:` with `except Exception:`
  - Add logging for all catches
  - Never catch KeyboardInterrupt

### Database Connection Cleanup Not Guaranteed
**Issue:** Not all code paths properly close database connections
- Files: `web/db_queries.py` (get_db_connection pattern), multiple data collection scripts
- Symptoms: Connection pool exhaustion, "pool exhausted" errors under load
- Trigger: Exceptions during query execution before finally block
- Pattern: `conn.close()` at end of function rather than in finally block consistently
- Fix approach:
  - Use context manager pattern: `with get_db_connection() as conn:`
  - Ensure finally blocks exist in all places
  - Add connection pool monitoring/diagnostics

### Silent JSON Loading Failures
**Issue:** JSON file loading silently degrades instead of failing explicitly
- Files: `services/clustering_service.py` lines 44-59, 115-124
- Symptoms:
  - Falls back to database when JSON missing (no user warning logged)
  - Dashboard may show stale/incorrect data silently
- Trigger: Missing `clustering_results.json` file
- Code: Falls back to DB query without raising error
- Fix approach:
  - Raise exception if expected file missing
  - Log clearly what's happening
  - Make data source explicit to user

### Bare Pass in Exception Handlers
**Issue:** Multiple exception handlers just `pass` without logging
- Example: `web/views/clustering_results.py:64-66` - GPT error caught but ignored
- Impact: Silent failures make debugging difficult
- Fix approach: Add logging to all error handlers

---

## Security Considerations

### API Keys Printed in Debug Output
**Issue:** DEBUG print statements expose partial API key information
- Files: `web/app.py` (lines 72-78), `common/openai_client.py` (line 117)
- Risk:
  - Logs may be captured and stored insecurely
  - CI/CD logs might expose API key prefixes
  - Accidentally committed debug output could leak secrets
- Code: `print(f"✅ OpenAI API 키 로드 성공 (길이: {len(api_key)})")` shows key length/patterns
- Recommendations:
  - Remove all debug prints containing secret info
  - Use logging with sanitized output
  - Never print API key length/patterns in production
  - Use masked format like "sk-****...****" only

### No Input Validation on SQL Queries
**Issue:** Some direct SQL construction without parameterized queries
- Files: Potential in various collection scripts
- Risk: SQL injection
- Recommendations:
  - Audit all SQL constructions
  - Ensure all parameters use prepared statements (`%s` placeholders)
  - Use ORM where possible

### .env.example Not Restricted
**Issue:** `.env.example` exists but contains template values that could mislead
- Files: `.env.example`
- Risk: Users might accidentally commit real `.env` with secrets
- Recommendations:
  - Keep `.env` in `.gitignore` (appears correct)
  - Document in README: never commit `.env`
  - Use pre-commit hooks to detect `.env` commits

### Environment Variable Overrides
**Issue:** Environment variables checked in multiple orderings, potential for confusion
- Files: `common/db.py`, `web/db_queries.py`, `worker/pipeline/db.py`
- Risk: Different precedence in different modules could lead to using wrong database
- Recommendations:
  - Document variable precedence clearly
  - Centralize precedence logic
  - Test precedence explicitly

---

## Performance Bottlenecks

### Inefficient Clustering Service JSON Loading (Cached but Repeated)
**Issue:** JSON file loaded multiple times per request despite caching
- Files: `services/clustering_service.py` lines 44-59
- Problem:
  - `_load_json()` called multiple times per request
  - 782KB file loaded into memory each time
  - No expiration/invalidation strategy
- Impact:
  - Memory usage bloat if many requests
  - Unnecessary file I/O
  - Slow response times for large clusters
- Improvement path:
  - Use Streamlit's `@st.cache_data` decorator for JSON loading
  - Implement TTL-based cache invalidation
  - Consider async loading

### No Query Pagination
**Issue:** DB queries fetch all results without pagination
- Files: `web/db_queries.py` (get_executive_overview, get_clustering_results_from_db, etc.)
- Problem:
  - SELECT without LIMIT/OFFSET on potentially large result sets
  - All data loaded into pandas DataFrame in memory
  - Dashboard could slow with large datasets
- Improvement path:
  - Add pagination to dashboard views
  - Implement LIMIT/OFFSET in queries
  - Stream large result sets

### Blocking API Calls Without Timeout
**Issue:** OpenAI API calls without explicit timeout configuration
- Files: `services/gpt_service.py`, `common/openai_client.py`
- Problem:
  - Could hang indefinitely if API unresponsive
  - No timeout specified on requests
  - Dashboard would freeze waiting for response
- Improvement path:
  - Add timeout to OpenAI client initialization
  - Implement request-level timeouts
  - Add async/concurrent request handling

### Linear Loop Performance in Clustering
**Issue:** Medoid selection uses O(n²) distance calculation
- Files: `worker/pipeline/clustering.py:83-100`
- Problem:
  - Nested loops calculate pairwise distances
  - Scales poorly with cluster size (10+ documents = noticeable slowdown)
  - No vectorization used
- Improvement path:
  - Use numpy broadcasting instead of loops
  - Implement distance matrix once, reuse
  - Profile and optimize for datasets >1000 docs

---

## Fragile Areas

### Text Embedding With Fallback But No Recovery
**Issue:** Embedding truncation has multiple fallback layers but no clear failure mode
- Files: `worker/pipeline/embedding.py:30-65`
- Why fragile:
  - tiktoken ImportError caught silently
  - Falls back to character-based truncation (imprecise)
  - No warning if truncation occurs
  - May produce inconsistent embeddings across runs
- Files affected: Any pipeline using embeddings

### Dependency on External JSON File
**Issue:** Dashboard hard-depends on `clustering_results.json` file existing
- Files: `services/clustering_service.py`, `web/app.py`
- Why fragile:
  - File not tracked in git (data/ directory?)
  - No fallback if file missing
  - Could fail silently and show empty dashboard
  - Deployment breaks if file not copied to container

### Railway SSL Handling Fragile
**Issue:** SSL mode detection uses string matching on database URL
- Files: `worker/pipeline/db.py:88-101`, `common/db.py` (duplicated)
- Why fragile:
  - Multiple patterns checked with string `.lower()`
  - URL parsing is brittle (manual string manipulation)
  - Could fail if Railway changes domain patterns
  - No validation that SSL was actually applied
- Improvements:
  - Use URL parsing library (urllib)
  - Validate SSL negotiation after connection
  - Test with actual Railway domains

### Connection Pool Exhaustion Fallback
**Issue:** Debug fallback allows direct connections when pool exhausted
- Files: `worker/pipeline/db.py:162-191`
- Why fragile:
  - Fallback only enabled with `DB_ALLOW_DIRECT_FALLBACK=true`
  - Creates untracked direct connections outside pool
  - Could mask connection leak issues
  - Not production-safe
- Improvements:
  - Remove fallback from production code
  - Implement proper connection leak detection
  - Add metrics for pool exhaustion

### GPT Service With No Fallback
**Issue:** GPT operations fail completely if OpenAI unavailable
- Files: `services/gpt_service.py:55-56`, `web/views/clustering_results.py:50-66`
- Why fragile:
  - No graceful degradation
  - Dashboard shows blank/error if OpenAI down
  - Checked at runtime, not startup
- Improvements:
  - Pre-compute summaries at pipeline time (not UI time)
  - Cache GPT results
  - Show cached version if API unavailable

### Streamlit Module Reload Hack
**Issue:** Force reload of modules to handle Streamlit caching
- Files: `web/views/clustering_results.py:20-22`
- Why fragile:
  - Hacky workaround, not root fix
  - Importlib.reload() side effects unpredictable
  - Could cause stale code execution if reload fails
- Better approach:
  - Refactor to avoid circular imports
  - Use Streamlit's session state properly
  - Structure modules to be reloadable naturally

---

## Test Coverage Gaps

### No Unit Tests for Core Pipeline Logic
**Issue:** Limited test coverage for data processing pipelines
- What's not tested:
  - `worker/pipeline/preprocess.py` - text cleaning logic
  - `worker/pipeline/clustering.py` - medoid selection algorithm
  - `worker/pipeline/embedding.py` - batch processing, truncation
  - Database operations (pooling, retry logic)
- Files: Only `tests/test_db_pool_smoke.py` exists (smoke test only)
- Priority: **High** - Core data integrity depends on these

### No Integration Tests
**Issue:** No tests for end-to-end pipeline execution
- What's not tested:
  - Full collect → preprocess → cluster → label workflow
  - Database migrations
  - Error recovery in partial failures
- Priority: **High** - Mode failures impact all data

### No Web/UI Tests
**Issue:** No tests for Streamlit dashboard functionality
- What's not tested:
  - DB query result handling
  - JSON file loading
  - GPT service integration
  - View rendering with various data states (empty, error, normal)
- Priority: **Medium** - UI errors are visible but not caught

### No API Contract Tests
**Issue:** External API integrations (Apify, SerpAPI, OpenAI) untested
- What's not tested:
  - Retry/backoff logic for API failures
  - Rate limiting handling
  - Error response parsing
  - Timeout behavior
- Priority: **Medium** - API failures impact collection

### No Load/Performance Tests
**Issue:** No performance baselines or load testing
- What's not tested:
  - Database query performance with large datasets
  - Clustering algorithm scalability (1K+ documents)
  - Memory usage under load
  - Connection pool exhaustion scenarios
- Priority: **Low** - Important for production scaling

### No Regression Tests for Data Quality
**Issue:** No tests to catch data quality degradation
- What's not tested:
  - Embedding consistency
  - Cluster stability
  - Duplicate detection
  - Text preprocessing correctness
- Priority: **High** - Core output quality must be validated

---

## Additional Concerns

### Documentation Gaps
- PoC vs Production: Unclear what's production-ready vs experimental
- Script Purpose: 44 collection scripts with no clear guidance on which to use
- Error Handling: No documented error recovery procedures
- Performance: No documented performance targets or SLAs

### Configuration Management
- No configuration validation at startup
- Missing environment variables silently use defaults
- No way to see effective configuration at runtime
- Hard to distinguish development vs production settings

### Logging Consistency
- Mix of `print()`, `logger.info()`, and `st.write()` for output
- No centralized logging configuration
- Hard to trace execution flow across modules
- No structured logging for machine analysis

---

*Concerns audit: 2026-02-18*
