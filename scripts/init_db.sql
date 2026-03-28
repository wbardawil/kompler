-- Kompler: PostgreSQL initialization
-- Extensions required for the platform

-- Vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Full-text search (built-in, but ensure configs)
-- tsvector is built into PostgreSQL, no extension needed

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Apache AGE for graph queries (Cypher support)
-- Note: AGE requires separate installation on the Docker image.
-- For MVP, we use adjacency tables for graph. AGE added in Phase 2.
-- CREATE EXTENSION IF NOT EXISTS age;

-- Row-Level Security will be enabled per-table in migrations
