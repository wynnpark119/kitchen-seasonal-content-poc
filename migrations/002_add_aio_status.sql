-- Add aio_status column to raw_serp_aio table
-- Status values: AVAILABLE, NOT_AVAILABLE, ERROR

ALTER TABLE raw_serp_aio
ADD COLUMN IF NOT EXISTS aio_status VARCHAR(20) DEFAULT 'NOT_AVAILABLE';

-- Add index for status queries
CREATE INDEX IF NOT EXISTS idx_raw_serp_aio_status ON raw_serp_aio(aio_status);

-- Add comment
COMMENT ON COLUMN raw_serp_aio.aio_status IS 'AI Overview availability status: AVAILABLE, NOT_AVAILABLE, ERROR';
