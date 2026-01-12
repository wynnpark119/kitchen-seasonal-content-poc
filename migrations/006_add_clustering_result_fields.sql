-- Migration: Add clustering result fields to clusters table
-- Version: 6.0
-- Created: 2025-01-XX

-- ============================================================================
-- Add clustering result fields to clusters table
-- ============================================================================

-- topic_category 컬럼 추가
ALTER TABLE clusters 
ADD COLUMN IF NOT EXISTS topic_category VARCHAR(50);

-- sub_cluster_index 컬럼 추가
ALTER TABLE clusters 
ADD COLUMN IF NOT EXISTS sub_cluster_index INTEGER;

-- top_keywords 컬럼 추가 (JSONB 배열)
ALTER TABLE clusters 
ADD COLUMN IF NOT EXISTS top_keywords JSONB;

-- summary 컬럼 추가
ALTER TABLE clusters 
ADD COLUMN IF NOT EXISTS summary TEXT;

-- cluster_metadata 컬럼 추가 (추가 메타데이터를 JSONB로 저장)
ALTER TABLE clusters 
ADD COLUMN IF NOT EXISTS cluster_metadata JSONB;

-- topic_category 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_clusters_topic_category ON clusters(topic_category);

-- sub_cluster_index 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_clusters_sub_cluster_index ON clusters(sub_cluster_index);

-- top_keywords GIN 인덱스 추가 (JSONB 쿼리용)
CREATE INDEX IF NOT EXISTS idx_clusters_top_keywords ON clusters USING gin (top_keywords);

-- Comments
COMMENT ON COLUMN clusters.topic_category IS 'Topic category: SPRING_RECIPES, SPRING_KITCHEN_STYLING, REFRIGERATOR_ORGANIZATION, VEGETABLE_PREP_HANDLING';
COMMENT ON COLUMN clusters.sub_cluster_index IS 'Sub-cluster index within the topic category';
COMMENT ON COLUMN clusters.top_keywords IS 'Top keywords for the cluster (JSONB array)';
COMMENT ON COLUMN clusters.summary IS 'Cluster summary text';
COMMENT ON COLUMN clusters.cluster_metadata IS 'Additional cluster metadata (JSONB)';
