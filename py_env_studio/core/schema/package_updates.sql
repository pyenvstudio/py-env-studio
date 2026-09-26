-- SQL templates: per-environment package-update cache.

-- name: ensure_environment
INSERT OR IGNORE INTO environments (env_name, env_path, created_at) VALUES (?, ?, ?)

-- name: create_package_update_cache
CREATE TABLE IF NOT EXISTS package_update_cache (
    env_id INTEGER PRIMARY KEY,
    outdated_count INTEGER,
    outdated_packages TEXT,
    last_checked_at TEXT NOT NULL,
    package_manager TEXT NOT NULL,
    error TEXT,
    FOREIGN KEY (env_id) REFERENCES environments(env_id) ON DELETE CASCADE
)

-- name: add_outdated_packages_column
ALTER TABLE package_update_cache ADD COLUMN outdated_packages TEXT

-- name: get_cached_package_updates
SELECT outdated_count, last_checked_at, package_manager, error, outdated_packages
FROM package_update_cache WHERE env_id=?

-- name: save_package_update_cache
INSERT INTO package_update_cache (env_id, outdated_count, outdated_packages, last_checked_at, package_manager, error)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(env_id) DO UPDATE SET
    outdated_count=excluded.outdated_count,
    outdated_packages=excluded.outdated_packages,
    last_checked_at=excluded.last_checked_at,
    package_manager=excluded.package_manager,
    error=excluded.error

-- name: delete_package_update_cache
DELETE FROM package_update_cache
WHERE env_id=(SELECT env_id FROM environments WHERE env_name=?)