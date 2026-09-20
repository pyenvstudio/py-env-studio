-- SQL templates: Python Install Manager online-metadata cache.
-- Normalized release rows are written in one DELETE + batch INSERT per
-- refresh; a failed online refresh never touches existing rows.

-- name: select_metadata_by_provider
SELECT metadata_json FROM python_runtime_metadata WHERE provider=?

-- name: select_cache_state
SELECT last_updated FROM python_runtime_cache_state WHERE provider=?

-- name: delete_metadata_by_provider
DELETE FROM python_runtime_metadata WHERE provider=?

-- name: insert_metadata_row
INSERT OR REPLACE INTO python_runtime_metadata
(provider, version, release_status, architecture, implementation, metadata_json, last_updated)
VALUES (?, ?, ?, ?, ?, ?, ?)

-- name: upsert_cache_state
INSERT OR REPLACE INTO python_runtime_cache_state
(provider, last_updated, last_error) VALUES (?, ?, NULL)

-- name: record_cache_error
INSERT INTO python_runtime_cache_state (provider, last_updated, last_error)
VALUES (?, ?, ?)
ON CONFLICT(provider) DO UPDATE SET last_error=excluded.last_error
