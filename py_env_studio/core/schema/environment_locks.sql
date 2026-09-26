-- SQL templates: environment-specific PEP 751 lock metadata.

-- name: create_environment_lock_metadata
CREATE TABLE IF NOT EXISTS environment_lock_metadata (
    env_id INTEGER PRIMARY KEY,
    lock_file_path TEXT NOT NULL,
    lock_format TEXT NOT NULL,
    lock_version TEXT NOT NULL,
    lock_created_at TEXT NOT NULL,
    lock_updated_at TEXT NOT NULL,
    lock_hash TEXT NOT NULL,
    lock_status TEXT NOT NULL,
    last_verified_at TEXT,
    FOREIGN KEY (env_id) REFERENCES environments(env_id) ON DELETE CASCADE
)

-- name: get_environment_lock_metadata
SELECT lock_file_path, lock_format, lock_version, lock_created_at,
       lock_updated_at, lock_hash, lock_status, last_verified_at
FROM environment_lock_metadata WHERE env_id=?

-- name: upsert_environment_lock_metadata
INSERT INTO environment_lock_metadata (
    env_id, lock_file_path, lock_format, lock_version, lock_created_at,
    lock_updated_at, lock_hash, lock_status, last_verified_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(env_id) DO UPDATE SET
    lock_file_path=excluded.lock_file_path,
    lock_format=excluded.lock_format,
    lock_version=excluded.lock_version,
    lock_updated_at=excluded.lock_updated_at,
    lock_hash=excluded.lock_hash,
    lock_status=excluded.lock_status,
    last_verified_at=excluded.last_verified_at

-- name: delete_environment_lock_metadata
DELETE FROM environment_lock_metadata WHERE env_id=?