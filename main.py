import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
os.environ.pop("SSLKEYLOGFILE", None)  # Prevents Windows SSL PermissionError on Documents folder
load_dotenv()

from ingestion.extractor import extract_report_text
from ingestion.parser import parse_biomarkers_with_llm
from ingestion.validator import ReportValidator, TrainingMode
from ingestion.db_loader import DatabaseLoader, DEFAULT_DB_PATH
from engine.routine_engine import generate_routine
from engine.pdf_exporter import export_routine_to_pdf



def save_routine_to_db(
    db: DatabaseLoader,
    report_id: int,
    user_profile: dict,
    validation_result: dict,
    engine_result: dict,
) -> int:
    """Creates workout_routines table in mvp_fitness.db if needed and persists the output."""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_routines (
                routine_id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                training_mode TEXT,
                relevance_percentage REAL,
                goal TEXT,
                experience TEXT,
                days_per_week INTEGER,
                duration_mins INTEGER,
                intensity_cap TEXT,
                rules_json TEXT,
                routine_markdown TEXT,
                created_at TEXT,
                FOREIGN KEY (report_id) REFERENCES lab_reports (report_id)
            )
        """)

        cursor.execute(
            """
            INSERT INTO workout_routines (
                report_id, training_mode, relevance_percentage, goal, experience,
                days_per_week, duration_mins, intensity_cap, rules_json,
                routine_markdown, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                validation_result.get("training_mode"),
                validation_result.get("relevance_percentage"),
                user_profile.get("goal"),
                user_profile.get("experience"),
                user_profile.get("days_per_week"),
                user_profile.get("duration_mins"),
                engine_result["rules"].get("intensity_cap"),
                json.dumps(engine_result["rules"]),
                engine_result["routine_markdown"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        routine_id = cursor.lastrowid
        conn.commit()
    return routine_id


def _execute_validation_and_engine(
    db: DatabaseLoader,
    report_id: int,
    parsed_data: dict,
    user_profile: dict,
    model_name: str,
) -> dict:
    """Shared validation + routine generation logic for both new and existing reports."""
    validator = ReportValidator()
    training_mode: TrainingMode = user_profile.get("training_mode", "general_fitness")

    validation = validator.validate(
        parsed_data=parsed_data,
        training_mode=training_mode,
        age=user_profile.get("age"),
    )

    print(
        f"      -> Validation: {validation['verdict']} "
        f"({validation['relevance_percentage']}% relevance for {training_mode})"
    )

    # Stop early if the blood report lacks core markers for the selected training mode
    if not validation["usable"]:
        return {
            "status": "insufficient_biomarkers",
            "report_id": report_id,
            "validation": validation,
            "routine_markdown": (
                f"⚠️ **{validation['verdict']}**\n\n{validation['message']}\n\n"
                f"**Missing Recommended Tests:** {', '.join(validation['missing_biomarkers'])}"
            ),
        }

    # Pass missing biomarker context to the engine so the LLM notes any blind spots
    enriched_profile = {
        **user_profile,
        "training_mode": training_mode,
        "missing_biomarkers": validation["missing_biomarkers"],
    }

    print(f"      -> Generating personalized routine via Ollama ({model_name})...")
    engine_result = generate_routine(parsed_data, enriched_profile, model_name=model_name)

    routine_id = save_routine_to_db(
        db, report_id, enriched_profile, validation, engine_result
    )
    print(f"      -> Saved routine to {DEFAULT_DB_PATH.name} (routine_id={routine_id})")
    pdf_out_dir = Path(__file__).resolve().parent / "generated_pdfs"
    saved_pdf = export_routine_to_pdf(
        output_dir=pdf_out_dir,
        parsed_data=parsed_data,
        user_profile=enriched_profile,
        pipeline_output={
            "report_id": report_id,
            "routine_id": routine_id,
            "validation": validation,
            **engine_result,
        },
    )
    print(f" -> Exported PDF report to {saved_pdf}")


    return {
        "report_id": report_id,
        "routine_id": routine_id,
        "validation": validation,
        **engine_result,
    }


def run_from_pdf(
    file_path: str | Path,
    user_profile: dict,
    model_name: str = "gemini-3.8-flash",
) -> dict:
    """Full end-to-end pipeline: PDF/Image -> Extract -> Parse -> DB -> Validate -> Engine."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Report file not found: {file_path}")

    db = DatabaseLoader(DEFAULT_DB_PATH)

    print(f"[1/4] Extracting text from {file_path.name}...")
    raw_text = extract_report_text(file_path)

    print("[2/4] Parsing biomarkers into structured JSON...")
    parsed_data = parse_biomarkers_with_llm(raw_text)

    print("[3/4] Saving parsed report to SQLite...")
    report_id = db.save_report(parsed_data, source_file=file_path.name)
    print(f"      -> Saved to {DEFAULT_DB_PATH.name} (report_id={report_id})")

    print("[4/4] Validating relevance & generating workout routine...")
    return _execute_validation_and_engine(
        db, report_id, parsed_data, user_profile, model_name
    )


def run_from_existing_report(
    report_id: int,
    user_profile: dict,
    model_name: str = "gemini-3.8-flash",
) -> dict:
    """Runs validation and routine generation directly on a report_id in mvp_fitness.db."""
    db = DatabaseLoader(DEFAULT_DB_PATH)

    print(f"[1/2] Loading report_id={report_id} from {DEFAULT_DB_PATH.name}...")
    parsed_data = db.get_report(report_id)
    if not parsed_data:
        raise ValueError(f"report_id={report_id} not found in {DEFAULT_DB_PATH}")

    print("[2/2] Validating relevance & generating workout routine...")
    return _execute_validation_and_engine(
        db, report_id, parsed_data, user_profile, model_name
    )


if __name__ == "__main__":
    sample_user_profile = {
        "training_mode": "hybrid_athlete",
        "goal": "Athletic Conditioning & Lean Muscle",
        "experience": "Intermediate",
        "days_per_week": 4,
        "duration_mins": 60,
        "conditions": "None",
    }

    # Test with report_id=1 already in mvp_fitness.db
    output = run_from_existing_report(report_id=1, user_profile=sample_user_profile)

    # Or run with a fresh PDF/Image upload:
    # output = run_from_pdf("data/Malereport1.pdf", sample_user_profile)

    print("\n" + "=" * 60)
    print(f"REPORT VALIDATION: {output['validation']['verdict']} ({output['validation']['relevance_percentage']}%)")
    if output["validation"]["missing_biomarkers"]:
        print(f"Missing Tests for Mode: {', '.join(output['validation']['missing_biomarkers'])}")
    print("=" * 60)

    if "rules" in output:
        print("\nCLINICAL BIOMARKER RULES:")
        for flag in output["rules"]["clinical_flags"]:
            print(f"- {flag}")

    print("\n" + "=" * 60)
    print("PERSONALIZED WORKOUT ROUTINE")
    print("=" * 60)
    print(output["routine_markdown"])
