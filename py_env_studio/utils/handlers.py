from datetime import datetime
import json,os
import sqlite3
from py_env_studio.core.env_manager import VENV_DIR, DB_FILE,MATRIX_FILE 
# print(f"{DB_FILE=}")
# ===================== Data Helper =====================

class DataHelper:
    """Operations in JSON file (acts like DBHelper but with JSON)."""

    @staticmethod
    def _load_data():
        """Load JSON data from file (or return default structure)."""
        if not os.path.exists(MATRIX_FILE):
            return {"environments": [], "env_vulnerability_info": []}

        with open(MATRIX_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"environments": [], "env_vulnerability_info": []}

    @staticmethod
    def _save_data(data):
        """Save data back to JSON file."""
        with open(MATRIX_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # ===================== Environment Methods =====================

    @staticmethod
    def get_or_create_env(env_name, env_path):
        """Return env_id for env_name, create if not exists."""
        data = DataHelper._load_data()

        for env in data["environments"]:
            if env["env_name"] == env_name:
                return env["env_id"]

        # assign new id
        new_id = len(data["environments"]) + 1
        new_env = {
            "env_id": new_id,
            "env_name": env_name,
            "env_path": env_path,
        }
        data["environments"].append(new_env)
        DataHelper._save_data(data)

        return new_id

    # ===================== Vulnerability Methods =====================

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        """Save vulnerabilities for an environment."""
        data = DataHelper._load_data()

        new_vid = len(data["env_vulnerability_info"]) + 1
        record = {
            "vid": new_vid,
            "env_id": env_id,
            "vulnerabilities": vulnerabilities_json,
        }

        data["env_vulnerability_info"].append(record)
        DataHelper._save_data(data)

    @staticmethod
    def get_vulnerability_info(env_id):
        """Retrieve vulnerabilities for a given env_id."""
        data = DataHelper._load_data()

        results = [
            rec for rec in data["env_vulnerability_info"] if rec["env_id"] == env_id
        ]

        return results if results else None

# ===================== Database Helper =====================
class DBHelper:
    @staticmethod
    def init_db():
        """Initialize DB only if file doesn't exist (first run)."""
        if not os.path.exists(DB_FILE):
            try:
                os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
                with sqlite3.connect(DB_FILE) as conn:
                    cur = conn.cursor()
                    
                    # Create environments table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS environments (
                            env_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            env_name TEXT UNIQUE NOT NULL,
                            env_path TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create env_vulneribility_info table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS env_vulneribility_info (
                            vid INTEGER PRIMARY KEY AUTOINCREMENT,
                            env_id INTEGER NOT NULL,
                            vulneribilities TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (env_id) REFERENCES environments(env_id)
                        )
                    """)
                    
                    print("✅ Database initialized.")
            except sqlite3.Error as e:
                print(f"Database error: {e}")
                raise
            except Exception as e:
                print(f"Unexpected error: {e}")
                raise
        else:
            # File exists, no need to recreate
            pass


    @staticmethod
    def get_or_create_env(env_name):
        """Return env_id for env_name, create if not exists."""
        from py_env_studio.core.env_manager import VENV_DIR
        env_path = os.path.join(VENV_DIR, env_name)
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT env_id FROM environments WHERE env_name=?", (env_name,))
        row = cur.fetchone()
        if row:
            env_id = row[0]
        else:
            cur.execute("INSERT INTO environments (env_name, env_path, created_at) VALUES (?, ?, ?)", (env_name, env_path, datetime.now()))
            env_id = cur.lastrowid
            conn.commit()
        conn.close()
        return env_id

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        conn = sqlite3.connect(DB_FILE)
        try:
            cur = conn.cursor()
            with conn:
                cur.execute(
                    "INSERT INTO env_vulneribility_info (env_id, vulneribilities, created_at) VALUES (?, ?, ?)",
                    (env_id, json.dumps(vulnerabilities_json), datetime.now())
                )
        except Exception as e:
            print(f"Error saving vulnerability info: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_vulnerability_info(env_name):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""SELECT 
    JSON_OBJECT(
        'vulnerability_insights', 
        JSON_ARRAY(
            JSON_GROUP_OBJECT(
                CAST(vid AS TEXT), 
                JSON_EXTRACT(vulneribilities, '$.vulnerability_insights')
            )
        )
    ) as result
FROM env_vulneribility_info evi 
                    JOIN environments e ON evi.env_id = e.env_id WHERE e.env_name=?
                    AND DATE(evi.created_at) = (SELECT MAX(DATE(created_at)) FROM env_vulneribility_info WHERE env_id = evi.env_id)

                    """, (env_name,))
        row = cur.fetchone()
        conn.close()
        if row:
            print(f"Retrieved vulnerability info for env_name {env_name}")
            return json.loads(row[0])
        return None

