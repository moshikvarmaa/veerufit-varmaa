import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "mvp_fitness.db"


class DatabaseLoader:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Lets you access columns by name
        return conn

    def _init_db(self):
        """Creates tables if they do not exist yet."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Patients / Reports Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_reports (
                    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    age REAL,
                    biological_sex TEXT,
                    source_file TEXT,
                    raw_json TEXT,
                    uploaded_at TEXT
                )
            """)

            # 2. Arbitrary Biomarkers Table (linked to report_id)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS biomarkers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    standard_key TEXT NOT NULL,
                    raw_test_name TEXT,
                    value REAL,
                    unit TEXT,
                    reference_range TEXT,
                    status TEXT,
                    FOREIGN KEY (report_id) REFERENCES lab_reports (report_id)
                )
            """)
            conn.commit()

    def save_report(self, parsed_data: dict, source_file: str = "uploaded_report.pdf") -> int:
        """
        Saves the parsed JSON from parser.py into SQLite.
        Returns the generated report_id.
        """
        patient = parsed_data.get("patient_context", {})
        biomarkers = parsed_data.get("biomarkers", {})
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Insert patient report record
            cursor.execute(
                """
                INSERT INTO lab_reports (patient_name, age, biological_sex, source_file, raw_json, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    patient.get("patient_name"),
                    patient.get("age"),
                    patient.get("biological_sex"),
                    source_file,
                    json.dumps(parsed_data),
                    timestamp,
                ),
            )
            report_id = cursor.lastrowid

            # Insert every arbitrary biomarker row
            biomarker_rows = [
                (
                    report_id,
                    standard_key,
                    details.get("raw_test_name"),
                    details.get("value"),
                    details.get("unit"),
                    details.get("reference_range"),
                    details.get("status"),
                )
                for standard_key, details in biomarkers.items()
            ]

            cursor.executemany(
                """
                INSERT INTO biomarkers (report_id, standard_key, raw_test_name, value, unit, reference_range, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                biomarker_rows,
            )
            conn.commit()

        return report_id

    def get_report(self, report_id: int) -> dict | None:
        """Fetches a saved report and its biomarkers back as a Python dictionary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lab_reports WHERE report_id = ?", (report_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return json.loads(row["raw_json"])

    def get_flagged_biomarkers(self, report_id: int) -> list[dict]:
        """Quickly fetches only 'low' or 'high' biomarkers for the workout engine."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT standard_key, raw_test_name, value, unit, reference_range, status
                FROM biomarkers
                WHERE report_id = ? AND status IN ('low', 'high')
                """,
                (report_id,),
            )
            return [dict(row) for row in cursor.fetchall()]