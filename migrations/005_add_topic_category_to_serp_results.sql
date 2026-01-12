-- Migration: Add topic_category to serp_results table
-- Version: 5.0
-- Created: 2025-01-XX

-- ============================================================================
-- Add topic_category column to serp_results
-- ============================================================================

-- topic_category 컬럼 추가 (NULL 허용, 기존 데이터 호환)
ALTER TABLE serp_results 
ADD COLUMN IF NOT EXISTS topic_category VARCHAR(50);

-- engine 컬럼 추가 (기본값: google)
ALTER TABLE serp_results 
ADD COLUMN IF NOT EXISTS engine VARCHAR(50) DEFAULT 'google';

-- dedup_hash 컬럼 추가 (중복 방지용)
ALTER TABLE serp_results 
ADD COLUMN IF NOT EXISTS dedup_hash TEXT;

-- topic_category 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_serp_results_topic_category ON serp_results(topic_category);

-- dedup_hash 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_serp_results_dedup_hash ON serp_results(dedup_hash);

-- 기존 UNIQUE 제약조건 확인 및 수정
-- 기존: UNIQUE(url, query)
-- 새로운: UNIQUE(topic_category, query, url)

-- 기존 제약조건 제거 (있을 경우 - 에러 무시)
-- ALTER TABLE serp_results DROP CONSTRAINT IF EXISTS uk_serp_result_url_query;

-- 새로운 UNIQUE 제약조건 추가 (topic_category, query, url)
-- NULL 값은 제외되므로 기존 데이터와 호환
-- 제약조건이 이미 존재하면 에러 발생할 수 있으므로 주의
-- ALTER TABLE serp_results 
-- ADD CONSTRAINT uk_serp_result_topic_query_url 
-- UNIQUE (topic_category, query, url);

-- Comments
COMMENT ON COLUMN serp_results.topic_category IS 'Topic category: SPRING_RECIPES, REFRIGERATOR_ORGANIZATION, VEGETABLE_PREP_HANDLING, SPRING_KITCHEN_STYLING';
COMMENT ON COLUMN serp_results.engine IS 'Search engine: google, bing, etc.';
COMMENT ON COLUMN serp_results.dedup_hash IS 'Hash for deduplication: SHA256(url + title)';
