-- Migration: Add GPT summary fields for monthly trend and representative posts
-- Version: 7.0
-- Created: 2025-01-XX

-- ============================================================================
-- Add GPT summary fields to clusters table
-- ============================================================================

-- monthly_trend_summary 컬럼 추가 (GPT가 생성한 월간 트렌드 분석 요약)
ALTER TABLE clusters 
ADD COLUMN IF NOT EXISTS monthly_trend_summary TEXT;

-- representative_posts_summary 컬럼 추가 (GPT가 생성한 대표 포스트 분석 요약)
ALTER TABLE clusters 
ADD COLUMN IF NOT EXISTS representative_posts_summary TEXT;

-- Comments
COMMENT ON COLUMN clusters.monthly_trend_summary IS 'GPT-generated summary of monthly trend analysis for this cluster';
COMMENT ON COLUMN clusters.representative_posts_summary IS 'GPT-generated summary of representative posts analysis for this cluster';
