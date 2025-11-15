-- Initialize NovaAvatar database

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial admin API key (replace with your own secure key!)
-- This is just for initial setup - should be changed immediately
INSERT INTO api_keys (id, key, name, description, is_active, permissions, rate_limit, created_at)
VALUES (
    uuid_generate_v4(),
    'novaavatar_dev_key_change_me_in_production',
    'Development Key',
    'Initial development API key - CHANGE IN PRODUCTION',
    true,
    '["*"]'::jsonb,
    1000,
    NOW()
) ON CONFLICT DO NOTHING;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_jobs(status);
CREATE INDEX IF NOT EXISTS idx_video_jobs_created_at ON video_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_items_scraped_at ON content_items(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_items_search_term ON content_items(search_term);
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp DESC);

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO novaavatar;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO novaavatar;
