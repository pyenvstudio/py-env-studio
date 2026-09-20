-- SQL templates: legacy schema migration (misspelled table fix-up).
-- The {source_col} placeholder in copy_legacy_scans is an identifier, not a
-- value: database.py validates it against a two-entry whitelist before
-- formatting. All other inputs use DB-API ? placeholders.

-- name: select_migration_flag
SELECT value FROM app_metadata WHERE key='legacy_migrated'

-- name: select_legacy_table
SELECT name FROM sqlite_master WHERE type='table' AND name='env_vulneribility_info'

-- name: pragma_legacy_table_info
PRAGMA table_info(env_vulneribility_info)

-- name: copy_legacy_scans
INSERT INTO env_vulnerability_info (env_id, vulnerabilities, created_at)
SELECT env_id, {source_col}, created_at
FROM env_vulneribility_info

-- name: mark_migrated
INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('legacy_migrated', '1')
