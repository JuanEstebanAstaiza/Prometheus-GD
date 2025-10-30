-- SGDI Initial Schema Migration
-- Migration: 0001_initial_schema
-- Description: Create initial database schema for SGDI system
-- Created: 2025-01-01

-- =====================================================
-- SCHEMA CREATION
-- =====================================================

-- Create schema if it doesn't exist (will be handled by database.py if DB_SCHEMA != 'public')

-- =====================================================
-- TABLES
-- =====================================================

-- Dependencies table (must be created first as it's referenced by other tables)
CREATE TABLE IF NOT EXISTS dependencies (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    code VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    full_name VARCHAR,
    role VARCHAR NOT NULL CHECK (role IN ('SUPER_ADMIN', 'ADMIN_DEP', 'WORKER', 'READER')),
    dependency_id VARCHAR REFERENCES dependencies(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Folders table
CREATE TABLE IF NOT EXISTS folders (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    parent_id VARCHAR REFERENCES folders(id),
    dependency_id VARCHAR NOT NULL REFERENCES dependencies(id),
    created_by VARCHAR REFERENCES users(id),
    path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id VARCHAR PRIMARY KEY,
    original_name VARCHAR NOT NULL,
    stored_name VARCHAR NOT NULL UNIQUE,
    mime_type VARCHAR,
    size_bytes BIGINT,
    checksum_sha256 VARCHAR,
    folder_id VARCHAR NOT NULL REFERENCES folders(id),
    dependency_id VARCHAR NOT NULL REFERENCES dependencies(id),
    uploaded_by VARCHAR REFERENCES users(id),
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    main_file_id VARCHAR REFERENCES files(id),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Action logs table
CREATE TABLE IF NOT EXISTS action_logs (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    user_role VARCHAR,
    action_type VARCHAR NOT NULL,
    target_type VARCHAR,
    target_id VARCHAR,
    details JSONB,
    ip_address VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Backup records table
CREATE TABLE IF NOT EXISTS backup_records (
    id VARCHAR PRIMARY KEY,
    filename VARCHAR,
    created_by VARCHAR REFERENCES users(id),
    size_bytes BIGINT,
    checksum_sha256 VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Refresh tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL REFERENCES users(id),
    token_hash VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    ip_address VARCHAR,
    user_agent TEXT
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    original_name VARCHAR NOT NULL,
    stored_name VARCHAR NOT NULL UNIQUE,
    mime_type VARCHAR,
    size_bytes BIGINT,
    checksum_sha256 VARCHAR,
    folder_id VARCHAR NOT NULL REFERENCES folders(id),
    dependency_id VARCHAR NOT NULL REFERENCES dependencies(id),
    uploaded_by VARCHAR REFERENCES users(id),
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    main_file_id VARCHAR REFERENCES files(id),
    file_metadata JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for files table
CREATE INDEX IF NOT EXISTS idx_files_folder_id ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_dependency_id ON files(dependency_id);
CREATE INDEX IF NOT EXISTS idx_files_uploaded_by ON files(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_files_main_file_id ON files(main_file_id);
CREATE INDEX IF NOT EXISTS idx_files_is_deleted ON files(is_deleted);
CREATE INDEX IF NOT EXISTS idx_files_mime_type ON files(mime_type);

-- Schema migrations table
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id VARCHAR PRIMARY KEY,
    applied BOOLEAN NOT NULL DEFAULT FALSE,
    applied_at TIMESTAMP WITH TIME ZONE,
    checksum VARCHAR(64),
    error_message TEXT
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Folders indexes
CREATE INDEX IF NOT EXISTS idx_folders_dependency_id ON folders(dependency_id);
CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON folders(parent_id);

-- Files indexes
CREATE INDEX IF NOT EXISTS idx_files_folder_id ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_dependency_id ON files(dependency_id);

-- Action logs indexes
CREATE INDEX IF NOT EXISTS idx_action_logs_user_id ON action_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_action_type ON action_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_action_logs_timestamp ON action_logs(timestamp);

-- =====================================================
-- TRIGGERS FOR UPDATED_AT
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dependencies_updated_at BEFORE UPDATE ON dependencies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_folders_updated_at BEFORE UPDATE ON folders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_files_updated_at BEFORE UPDATE ON files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================
