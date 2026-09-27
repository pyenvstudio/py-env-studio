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
    "vulnerability": {"insert_scan", "latest_scan_rows", "update_payload_by_vid"},
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
        ("vulnerability", "update_payload_by_vid"),
        ("runtime_cache", "select_metadata_by_provider"),
        ("runtime_cache", "select_cache_state"),
        ("runtime_cache", "delete_metadata_by_provider"),
        ("runtime_cache", "insert_metadata_row"),
        ("runtime_cache", "upsert_cache_state"),
        ("runtime_cache", "record_cache_error"),
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
    } <= tables


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
