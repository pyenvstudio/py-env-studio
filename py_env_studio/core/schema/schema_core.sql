-- SQL templates: core schema (app/environment/vulnerability tables).
-- Each statement is executed in file order by DatabaseManager.

-- name: enable_foreign_keys
PRAGMA foreign_keys = ON

-- name: create_app_metadata
CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)

-- name: create_environments
CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_name TEXT UNIQUE NOT NULL,
    env_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- name: create_env_vulnerability_info
CREATE TABLE IF NOT EXISTS env_vulnerability_info (
    vid INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL,
    vulnerabilities TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (env_id) REFERENCES environments(env_id)
)
