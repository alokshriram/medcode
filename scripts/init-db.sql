-- Create schemas for bounded contexts
CREATE SCHEMA IF NOT EXISTS workflow;
CREATE SCHEMA IF NOT EXISTS records;
CREATE SCHEMA IF NOT EXISTS catalogs;
CREATE SCHEMA IF NOT EXISTS users;

-- Grant permissions
GRANT ALL ON SCHEMA workflow TO postgres;
GRANT ALL ON SCHEMA records TO postgres;
GRANT ALL ON SCHEMA catalogs TO postgres;
GRANT ALL ON SCHEMA users TO postgres;
