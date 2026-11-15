"""Tests for the core/schema/*.sql template registry and its call sites."""
from __future__ import annotations

from pathlib import Path

import pytest

from py_env_studio.core import schema as sql
from py_env_studio.core.database import DatabaseManager


# Every template key referenced from Python code must exist in its .sql file.
EXPECTED_KEYS = {
    "schema_core": {
        "enable_foreign_keys",
        "create_app_metadata",
        "create_environments",
        "create_env_vulnerability_info",
    },
    "schema_runtime_cache": {
        "create_python_runtime_metadata",
        "create_python_runtime_cache_state",
    },
    "migration": {
        "select_migration_flag",
        "select_legacy_table",
        "pragma_legacy_table_info",
        "copy_legacy_scans",
        "mark_migrated",
    },
    "environments": {"get_env_id", "create_environment"},
    "project_contract": {
        "create_project_contract",
        "upsert_project_contract",
        "select_project_contract_by_path",
    },
    "vulnerability": {
        "insert_scan",
        "latest_scan_rows",
        "scan_history_rows",
        "update_payload_by_vid",
    },
    "runtime_cache": {
        "select_metadata_by_provider",
        "select_cache_state",
        "delete_metadata_by_provider",
        "insert_metadata_row",
        "upsert_cache_state",
        "record_cache_error",
    },
    "environment_locks": {
        "create_environment_lock_metadata",
        "get_environment_lock_metadata",
        "upsert_environment_lock_metadata",
        "delete_environment_lock_metadata",
    },
    "vulnerability_intelligence": {
        "create_vulnerability_intelligence_scans",
        "create_vulnerability_intelligence_queries",
        "create_vulnerability_intelligence_observations",
        "create_vulnerability_intelligence_scan_env_index",
        "create_vulnerability_intelligence_package_index",
        "create_vulnerability_intelligence_dependency_links",
        "create_vulnerability_intelligence_dependency_index",
        "migrate_vulnerability_intelligence_add_aliases_json",
        "migrate_vulnerability_intelligence_add_published_at",
        "migrate_vulnerability_intelligence_add_modified_at",
        "migrate_vulnerability_intelligence_add_withdrawn_at",
        "migrate_vulnerability_intelligence_add_cvss_json",
        "migrate_vulnerability_intelligence_add_cwe_ids_json",
        "migrate_vulnerability_intelligence_add_advisory_status",
        "migrate_vulnerability_intelligence_add_affected_release_count",
        "begin_vulnerability_intelligence_scan",
        "set_vulnerability_intelligence_scan_counts",
        "finish_vulnerability_intelligence_scan",
        "insert_vulnerability_intelligence_query",
        "get_vulnerability_intelligence_query_id",
        "insert_vulnerability_intelligence_observation",
        "insert_vulnerability_intelligence_dependency_link",
        "vulnerability_intelligence_dependencies",
        "successful_vulnerability_intelligence_dependency_history",
        "vulnerability_intelligence_history",
    },
}


def test_all_expected_templates_exist():
    for purpose, names in EXPECTED_KEYS.items():
        assert set(sql.available(purpose)) == names, purpose


def test_unknown_template_raises_helpful_key_error():
    with pytest.raises(KeyError, match="available"):
        sql.get("vulnerability", "no_such_statement")


def test_runtime_values_use_placeholders_not_interpolation():
    """Value-carrying statements must bind via ? (identifiers stay static)."""
    value_statements = [
        ("environments", "get_env_id"),
        ("environments", "create_environment"),
        ("project_contract", "upsert_project_contract"),
        ("project_contract", "select_project_contract_by_path"),
        ("vulnerability", "insert_scan"),
        ("vulnerability", "latest_scan_rows"),
        ("vulnerability", "scan_history_rows"),
        ("vulnerability", "update_payload_by_vid"),
        ("runtime_cache", "select_metadata_by_provider"),
        ("runtime_cache", "select_cache_state"),
        ("runtime_cache", "delete_metadata_by_provider"),
        ("runtime_cache", "insert_metadata_row"),
        ("runtime_cache", "upsert_cache_state"),
        ("runtime_cache", "record_cache_error"),
        ("vulnerability_intelligence", "begin_vulnerability_intelligence_scan"),
        ("vulnerability_intelligence", "set_vulnerability_intelligence_scan_counts"),
        ("vulnerability_intelligence", "finish_vulnerability_intelligence_scan"),
        ("vulnerability_intelligence", "insert_vulnerability_intelligence_query"),
        ("vulnerability_intelligence", "get_vulnerability_intelligence_query_id"),
        ("vulnerability_intelligence", "insert_vulnerability_intelligence_observation"),
        ("vulnerability_intelligence", "vulnerability_intelligence_history"),
        ("vulnerability_intelligence", "insert_vulnerability_intelligence_dependency_link"),
        ("vulnerability_intelligence", "vulnerability_intelligence_dependencies"),
        ("vulnerability_intelligence", "successful_vulnerability_intelligence_dependency_history"),
    ]
    for purpose, name in value_statements:
        body = sql.get(purpose, name)
        assert "?" in body, (purpose, name)
        assert "%s" not in body
    # Sole whitelisted identifier placeholder (validated in code).
    assert "{source_col}" in sql.get("migration", "copy_legacy_scans")


def test_initialize_database_creates_all_tables(tmp_path: Path):
    dbm = DatabaseManager(db_path=tmp_path / "schema-test.db")
    dbm.initialize_database()
    with dbm.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {
        "app_metadata",
        "environments",
        "env_vulnerability_info",
        "project_contract",
        "python_runtime_metadata",
        "python_runtime_cache_state",
        "environment_lock_metadata",
        "vulnerability_intelligence_scans",
        "vulnerability_intelligence_queries",
        "vulnerability_intelligence_observations",
        "vulnerability_intelligence_dependency_links",
    } <= tables


def test_initialize_database_additively_migrates_earlier_intelligence_table(tmp_path: Path):
    import sqlite3

    db_path = tmp_path / "previous-2.1.5.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""CREATE TABLE vulnerability_intelligence_observations (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER NOT NULL, scan_id INTEGER NOT NULL,
            package_name TEXT NOT NULL, normalized_package TEXT NOT NULL,
            package_version TEXT NOT NULL, vulnerability_id TEXT NOT NULL,
            source TEXT NOT NULL, affected_versions TEXT NOT NULL DEFAULT '[]',
            affected_ranges TEXT NOT NULL DEFAULT '[]', fixed_versions TEXT NOT NULL DEFAULT '[]',
            severity TEXT NOT NULL DEFAULT 'Unknown', vulnerability_status TEXT NOT NULL DEFAULT 'not fixed',
            observed_at TEXT NOT NULL, details_json TEXT NOT NULL,
            UNIQUE (query_id, vulnerability_id, source))""")
    DatabaseManager(db_path=db_path).initialize_database()
    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(vulnerability_intelligence_observations)")}
    assert {
        "aliases_json", "published_at", "modified_at", "withdrawn_at", "cvss_json",
        "cwe_ids_json", "advisory_status", "affected_release_count",
    } <= columns


def test_legacy_migration_copies_misspelled_table(tmp_path: Path):
    """End-to-end: old DB with env_vulneribility_info migrates its rows."""
    import sqlite3

    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE environments (env_id INTEGER PRIMARY KEY, env_name TEXT UNIQUE)"
    )
    conn.execute("INSERT INTO environments (env_id, env_name) VALUES (1, 'demo')")
    conn.execute(
        "CREATE TABLE env_vulneribility_info "
        "(vid INTEGER PRIMARY KEY, env_id INTEGER, vulneribilities TEXT, created_at TIMESTAMP)"
    )
    conn.execute(
        "INSERT INTO env_vulneribility_info (env_id, vulneribilities, created_at) "
        "VALUES (1, '{\"a\": 1}', CURRENT_TIMESTAMP)"
    )
    conn.commit()
    conn.close()

    DatabaseManager(db_path=db_path).initialize_database()

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM env_vulnerability_info").fetchone()[0]
    flag = conn.execute(
        "SELECT value FROM app_metadata WHERE key='legacy_migrated'"
    ).fetchone()[0]
    conn.close()
    assert count == 1
    assert flag == "1"
