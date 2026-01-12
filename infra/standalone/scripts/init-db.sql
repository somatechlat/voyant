-- =============================================================================
-- VOYANT Database Initialization Script
-- =============================================================================
-- Creates all required databases for the Voyant stack
-- Run automatically by PostgreSQL on first startup
-- =============================================================================

-- Create databases
CREATE DATABASE keycloak;
CREATE DATABASE datahub;
CREATE DATABASE lago;
CREATE DATABASE temporal;

-- Grant permissions to voyant user (already exists as POSTGRES_USER)
GRANT ALL PRIVILEGES ON DATABASE keycloak TO voyant;
GRANT ALL PRIVILEGES ON DATABASE datahub TO voyant;
GRANT ALL PRIVILEGES ON DATABASE lago TO voyant;
GRANT ALL PRIVILEGES ON DATABASE voyant TO voyant;

-- Connect to voyant database and create schema
\c voyant

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    tier VARCHAR(50) DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'professional', 'enterprise')),
    settings JSONB DEFAULT '{}',
    quota_config JSONB DEFAULT '{"max_sources": 10, "max_storage_gb": 10, "max_queries_per_day": 100}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Sources table
CREATE TABLE IF NOT EXISTS sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    connection_config JSONB NOT NULL,
    credentials_ref VARCHAR(255),
    airbyte_source_id VARCHAR(255),
    datahub_urn VARCHAR(500),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'connected', 'syncing', 'error', 'disabled')),
    sync_schedule VARCHAR(100),
    last_sync_at TIMESTAMPTZ,
    schema_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, name)
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    source_id UUID REFERENCES sources(source_id),
    job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('ingest', 'profile', 'quality', 'kpi', 'preset', 'sql')),
    preset_name VARCHAR(100),
    pipeline_type VARCHAR(50) CHECK (pipeline_type IN ('beam-spark', 'beam-flink', 'airbyte', 'direct')),
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    parameters JSONB,
    result_summary JSONB,
    artifact_ids UUID[],
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    datahub_run_id VARCHAR(255),
    upstream_urns TEXT[],
    downstream_urns TEXT[]
);

-- Artifacts table
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    job_id UUID REFERENCES jobs(job_id),
    source_id UUID REFERENCES sources(source_id),
    artifact_type VARCHAR(50) NOT NULL CHECK (artifact_type IN ('profile', 'quality', 'kpi', 'chart', 'report', 'model')),
    name VARCHAR(255) NOT NULL,
    format VARCHAR(50) NOT NULL CHECK (format IN ('html', 'json', 'csv', 'parquet', 'png', 'pdf')),
    storage_path VARCHAR(1000) NOT NULL,
    size_bytes BIGINT,
    checksum_sha256 VARCHAR(64),
    metadata JSONB,
    datahub_urn VARCHAR(500),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Billing customers table
CREATE TABLE IF NOT EXISTS billing_customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) UNIQUE,
    lago_customer_id VARCHAR(255) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(255),
    billing_email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Sessions table (for Redis backup)
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    tenant_id UUID REFERENCES tenants(tenant_id),
    data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sources_tenant ON sources(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_tenant ON artifacts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_job ON artifacts(job_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

-- Default tenant for local development
INSERT INTO tenants (tenant_id, name, display_name, tier) 
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Tenant', 'professional')
ON CONFLICT (name) DO NOTHING;

-- Log completion
DO $$ BEGIN RAISE NOTICE 'Voyant database initialization complete'; END $$;
