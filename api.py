import os
os.environ.pop("SSLKEYLOGFILE", None)

import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from ingestion.db_loader import DatabaseLoader, DEFAULT_DB_PATH
from main import run_from_pdf
from engine.gmail_sender import send_routine_via_gmail

app = FastAPI(title="VeeruFit API")

# Allow React dev server (localhost:5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/generate")
async def generate_plan(
    full_name: str = Form(...),
    email: str = Form(""),
    training_mode: str = Form("general_fitness"),
    goal: str = Form("Athletic Conditioning & Lean Muscle"),
    experience: str = Form("Intermediate"),
    days_per_week: int = Form(4),
    duration_mins: int = Form(60),
    conditions: str = Form("None"),
    report_file: UploadFile = File(...),
):
    try:
        temp_dir = Path(tempfile.mkdtemp())
        temp_path = temp_dir / report_file.filename
        temp_path.write_bytes(await report_file.read())

        user_profile = {
            "patient_name": full_name.strip(),
            "training_mode": training_mode,
            "goal": goal.strip(),
            "experience": experience,
            "days_per_week": days_per_week,
            "duration_mins": duration_mins,
            "conditions": conditions.strip() or "None",
        }

        output = run_from_pdf(
            file_path=temp_path,
            user_profile=user_profile,
            model_name="gemini-2.5-flash",
        )

        report_id = output["report_id"]
        db = DatabaseLoader(DEFAULT_DB_PATH)
        saved_report = db.get_report(report_id) or {}

        pdf_dir = Path(__file__).resolve().parent / "generated_pdfs"
        matching_pdfs = sorted(
            pdf_dir.glob(f"*_Report{report_id}_WorkoutPlan.pdf"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        pdf_filename = matching_pdfs[0].name if matching_pdfs else None

        email_sent = False
        if email.strip() and "@" in email and matching_pdfs:
            email_sent = send_routine_via_gmail(
                recipient_email=email.strip(),
                patient_name=full_name.strip(),
                pdf_path=matching_pdfs[0],
                training_mode=training_mode,
                intensity_cap=output.get("rules", {}).get("intensity_cap", "Standard"),
            )

        return {
            "status": "success",
            "report_id": report_id,
            "email_sent": email_sent,
            "pdf_filename": pdf_filename,
            "validation": output.get("validation", {}),
            "rules": output.get("rules", {}),
            "routine_markdown": output.get("routine_markdown", ""),
            "biomarkers": saved_report.get("biomarkers", {}),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
def download_pdf(filename: str):
    pdf_path = Path(__file__).resolve().parent / "generated_pdfs" / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(path=pdf_path, filename=filename, media_type="application/pdf")
