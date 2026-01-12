-- Add insights_json column to topic_qa_briefs table
-- Stores platform-specific insights: content_gap_analysis, execution_checklist, etc.

ALTER TABLE topic_qa_briefs
ADD COLUMN IF NOT EXISTS insights_json JSONB;

-- Add index for insights_json queries
CREATE INDEX IF NOT EXISTS idx_topic_qa_briefs_insights ON topic_qa_briefs USING gin (insights_json);

-- Add comment
COMMENT ON COLUMN topic_qa_briefs.insights_json IS 'Platform-specific insights: content_gap_analysis, execution_checklist, publishing_window, format_recommendations, evidence_strength, safety_and_claims_flags';
