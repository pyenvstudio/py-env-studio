from __future__ import annotations

from datetime import datetime
import json
import os

from py_env_studio.core.database import DatabaseManager
from py_env_studio.core.env_manager import DB_FILE, MATRIX_FILE, VENV_DIR
from py_env_studio.core import schema as sql


class DataHelper:
    """Operations in JSON file (acts like DBHelper but with JSON)."""

    @staticmethod
    def _load_data():
        if not os.path.exists(MATRIX_FILE):
            return {"environments": [], "env_vulnerability_info": []}

        with open(MATRIX_FILE, "r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                return {"environments": [], "env_vulnerability_info": []}

    @staticmethod
    def _save_data(data):
        with open(MATRIX_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)

    @staticmethod
    def get_or_create_env(env_name, env_path):
        data = DataHelper._load_data()

        for env in data["environments"]:
            if env["env_name"] == env_name:
                return env["env_id"]

        new_id = len(data["environments"]) + 1
        data["environments"].append(
            {
                "env_id": new_id,
                "env_name": env_name,
                "env_path": env_path,
            }
        )
        DataHelper._save_data(data)
        return new_id

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        data = DataHelper._load_data()

        new_vid = len(data["env_vulnerability_info"]) + 1
        data["env_vulnerability_info"].append(
            {
                "vid": new_vid,
                "env_id": env_id,
                "vulnerabilities": vulnerabilities_json,
            }
        )
        DataHelper._save_data(data)

    @staticmethod
    def get_vulnerability_info(env_id):
        data = DataHelper._load_data()
        results = [record for record in data["env_vulnerability_info"] if record["env_id"] == env_id]
        return results if results else None


class DBHelper:
    _dbm = DatabaseManager()

    @staticmethod
    def init_db():
        DBHelper._dbm.initialize_database()

    @staticmethod
    def get_or_create_env(env_name):
        env_path = os.path.join(VENV_DIR, env_name)
        with DBHelper._dbm.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql.get("environments", "get_env_id"), (env_name,))
            row = cur.fetchone()
            if row:
                return row[0]

            cur.execute(
                sql.get("environments", "create_environment"),
                (env_name, env_path, datetime.now()),
            )
            conn.commit()
            return cur.lastrowid

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        with DBHelper._dbm.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                sql.get("vulnerability", "insert_scan"),
                (env_id, json.dumps(vulnerabilities_json), datetime.now()),
            )
            conn.commit()

    @staticmethod
    def get_vulnerability_info(env_name):
        with DBHelper._dbm.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                sql.get("vulnerability", "latest_scan_rows"),
                (env_name,),
            )
            rows = cur.fetchall()

        if not rows:
            return {"vulnerability_insights": []}

        buckets = {}
        for vid, payload in rows:
            try:
                decoded = json.loads(payload) if isinstance(payload, str) else payload
            except Exception:
                continue
            buckets[str(vid)] = decoded.get("vulnerability_insights", decoded)

        return {"vulnerability_insights": [buckets]}
