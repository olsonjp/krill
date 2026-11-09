-- PostgreSQL initialization script for Krill
-- This script runs when the PostgreSQL container starts

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Set timezone
SET timezone = 'UTC';

-- Grant necessary permissions to the krill_user
GRANT ALL PRIVILEGES ON DATABASE krill TO krill_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO krill_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO krill_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO krill_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO krill_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO krill_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO krill_user;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Krill PostgreSQL database initialized successfully';
END $$;
