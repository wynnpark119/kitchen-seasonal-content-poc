# Testing Patterns

**Analysis Date:** 2026-02-18

## Test Framework

**Runner:**
- pytest (implied - standard Python test framework, not explicitly configured)
- No `pytest.ini`, `tox.ini`, or `setup.cfg` test configuration files present
- Minimal testing infrastructure (only 1 test file found)

**Config:**
- No explicit test configuration file
- Default pytest discovery would use: `test_*.py`, `*_test.py` patterns
- Test location: `/home/user/kitchen-seasonal-content-poc/tests/`

**Run Commands:**
```bash
pytest tests/                          # Run all tests in tests/ directory
pytest tests/test_db_pool_smoke.py     # Run specific test file
python -m pytest                       # Run tests using module invocation
```

## Test File Organization

**Location:**
- `tests/` directory at project root (single level, not nested by module)
- Test files colocated: `/home/user/kitchen-seasonal-content-poc/tests/test_db_pool_smoke.py`

**Naming:**
- Pattern: `test_*.py` (e.g., `test_db_pool_smoke.py`)
- Test functions: `test_*()` (e.g., `test_embedding_pool()`)
- Descriptive names indicating feature being tested

## Test Structure

**Suite Organization:**
```python
#!/usr/bin/env python3
"""Module docstring describing test purpose"""
import os
import sys
from pathlib import Path

# Setup Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import dependencies
from worker.pipeline.db import get_connection_pool, create_pipeline_run, update_pipeline_run
from worker.pipeline.embedding import generate_embeddings
from worker.pipeline.logging import setup_logger

# Module-level logger
logger = setup_logger("test_db_pool_smoke")

# Test function with main pattern
def test_embedding_pool():
    """Test description"""
    # 1. Environment validation
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

    # 2. Logging markers
    logger.info("=" * 60)
    logger.info("Test started")

    try:
        # 3. Test execution
        run_id = create_pipeline_run("test_embedding_pool", "running")
        stats = generate_embeddings(run_id, dry_run=False, max_docs=200)

        # 4. Assertions
        assert len(stats["errors"]) == 0, f"Errors occurred: {stats['errors']}"
        assert stats["posts_processed"] > 0, "No posts processed"

        # 5. Success logging
        logger.info("✅ 테스트 성공!")
        return stats

    except Exception as e:
        logger.error(f"테스트 실패: {e}", exc_info=True)
        update_pipeline_run(run_id, "failed", error_message=str(e))
        raise

# Entry point pattern
if __name__ == "__main__":
    try:
        stats = test_embedding_pool()
        print(f"\n✅ 테스트 통과: {stats['embeddings_created']}개 임베딩 생성 완료")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
```

## Mocking

**Framework:**
- Standard library `unittest.mock` (implicit - not explicitly imported in observed tests)
- Direct dependency injection preferred over mocking
- No mock libraries (mock, pytest-mock) installed or used

**Patterns:**
- Smoke testing approach: Test against real database and APIs with small data volumes
- Test parameters allow controlled scoping: `max_docs=200` for quick execution
- Dry-run mode for validation without side effects: `dry_run=False` explicit parameter
- Environment variable injection for configuration: `os.getenv("DATABASE_URL")`, `os.getenv("OPENAI_API_KEY")`
- Direct function calls without mocking external services (integration testing style)
- Pipeline state management via actual pipeline_runs table: `create_pipeline_run()`, `update_pipeline_run()`

## Coverage

**Requirements:**
- None enforced (no coverage configuration, no coverage reporting observed)
- Testing appears ad-hoc and manual rather than automated
- Single smoke test file suggests limited test coverage
- Focus on integration/smoke testing rather than comprehensive unit test coverage

## Test Types

**Unit Tests:**
- Limited: Only 1 test file found (`test_db_pool_smoke.py`)
- Scope: Tests database connection pool exhaustion with embedding generation (200 posts)
- Approach: Direct integration with live database and OpenAI API
- Purpose: Verify connection pool doesn't exhaust under moderate load
- Environment requirements: `DATABASE_URL` and `OPENAI_API_KEY` environment variables mandatory
- Success criteria: No pool timeout errors, all embeddings generated without errors

**Integration Tests:**
- Smoke tests that exercise real external systems (database, OpenAI API)
- Tests use actual data pipeline functions: `generate_embeddings()`, `create_pipeline_run()`
- Results tracked in `pipeline_runs` table for audit/debugging
- No test isolation (tests modify real database state)

**Manual Testing Patterns Observed:**
- Ad-hoc test scripts in root directory: `check_*.py`, `save_*.py` scripts for manual validation
- Script-based testing with logging and assertions
- Typical pattern:
  ```python
  if __name__ == "__main__":
      try:
          stats = test_embedding_pool()
          print(f"\n✅ 테스트 통과")
          sys.exit(0)
      except Exception as e:
          print(f"\n❌ 테스트 실패: {e}")
          sys.exit(1)
  ```

**Missing Test Areas:**
- No unit tests for service layers (GPTService, ClusteringService)
- No mocking of external API calls (OpenAI, ApifyClient, SerpAPI)
- No tests for web dashboard (Streamlit app)
- No tests for database queries or ORM models
- No performance/load testing
- No security/validation testing

---
*Testing analysis: 2026-02-18*
