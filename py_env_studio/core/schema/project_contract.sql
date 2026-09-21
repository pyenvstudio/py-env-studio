-- SQL templates: PES project contract persistence (Phase A.1).
-- pes.config holds the DECLARED contract (project intent); this table holds
-- the REGISTERED contract state (resolved through PES services).
-- DDL (create_*) is executed by DatabaseManager.initialize_database; all
-- runtime values use DB-API ? placeholders at the call site.

-- name: create_project_contract
CREATE TABLE IF NOT EXISTS project_contract (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT UNIQUE NOT NULL,
    project_name TEXT NOT NULL,
    environment_id TEXT NOT NULL,
    python_version TEXT NOT NULL,
    python_provider TEXT NOT NULL,
    package_manager TEXT NOT NULL,
    runtime_managed INTEGER NOT NULL DEFAULT 1,
    runtime_enabled INTEGER NOT NULL DEFAULT 0,
    runtime_auto_init INTEGER NOT NULL DEFAULT 1,
    config_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- name: upsert_project_contract
INSERT INTO project_contract
(project_path, project_name, environment_id, python_version, python_provider,
 package_manager, runtime_managed, runtime_enabled, runtime_auto_init, config_path)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(project_path) DO UPDATE SET
project_name=excluded.project_name,
environment_id=excluded.environment_id,
python_version=excluded.python_version,
python_provider=excluded.python_provider,
package_manager=excluded.package_manager,
runtime_managed=excluded.runtime_managed,
runtime_enabled=excluded.runtime_enabled,
runtime_auto_init=excluded.runtime_auto_init,
config_path=excluded.config_path,
updated_at=CURRENT_TIMESTAMP

-- name: select_project_contract_by_path
SELECT id, project_path, project_name, environment_id, python_version,
python_provider, package_manager, runtime_managed, runtime_enabled,
runtime_auto_init, config_path, created_at, updated_at
FROM project_contract WHERE project_path=?
