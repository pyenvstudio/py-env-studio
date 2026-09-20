-- SQL templates: runtime online-metadata cache schema.
-- Executed in file order by DatabaseManager, after schema_core.sql.

-- name: create_python_runtime_metadata
CREATE TABLE IF NOT EXISTS python_runtime_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    version TEXT NOT NULL,
    release_status TEXT,
    architecture TEXT,
    implementation TEXT,
    metadata_json TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, version)
)

-- name: create_python_runtime_cache_state
CREATE TABLE IF NOT EXISTS python_runtime_cache_state (
    provider TEXT PRIMARY KEY,
    last_updated TIMESTAMP NOT NULL,
    last_error TEXT
)
