
import os
os.environ.pop("SSLKEYLOGFILE", None)

import tempfile
import traceback
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "generated_pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)


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
        # 1. Save uploaded report temporarily
        temp_dir = Path(tempfile.mkdtemp())
        temp_path = temp_dir / Path(report_file.filename).name
        temp_path.write_bytes(await report_file.read())

        # 2. Build user profile
        user_profile = {
            "patient_name": full_name.strip(),
            "training_mode": training_mode,
            "goal": goal.strip(),
            "experience": experience,
            "days_per_week": days_per_week,
            "duration_mins": duration_mins,
            "conditions": conditions.strip() or "None",
        }

        # 3. Generate workout plan and PDF
        output = run_from_pdf(
            file_path=temp_path,
            user_profile=user_profile,
            model_name="gemini-3.8-flash",
        )

        report_id = output["report_id"]

        # 4. Retrieve saved report
        db = DatabaseLoader(DEFAULT_DB_PATH)
        saved_report = db.get_report(report_id) or {}

        # 5. Locate generated PDF
        matching_pdfs = sorted(
            PDF_DIR.glob(f"*_Report{report_id}_WorkoutPlan.pdf"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        pdf_filename = matching_pdfs[0].name if matching_pdfs else None

        # 6. Debug information
        print("\n========== PDF DEBUG ==========")
        print("REPORT ID:", report_id)
        print("PDF DIRECTORY:", PDF_DIR.resolve())
        print("DIRECTORY EXISTS:", PDF_DIR.exists())
        print("ALL PDF FILES:", [p.name for p in PDF_DIR.glob("*.pdf")])
        print("MATCHING PDFS:", [p.name for p in matching_pdfs])
        print("RETURNED FILENAME:", pdf_filename)
        print("================================\n")

        # 7. Send PDF by email if requested and available
        email_sent = False

        if email.strip() and "@" in email and matching_pdfs:
            email_sent = send_routine_via_gmail(
                recipient_email=email.strip(),
                patient_name=full_name.strip(),
                pdf_path=matching_pdfs[0],
                training_mode=training_mode,
                intensity_cap=output.get("rules", {}).get(
                    "intensity_cap", "Standard"
                ),
            )

        # 8. Return API response
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
        print("\n========== GENERATE API ERROR ==========")
        traceback.print_exc()
        print("ERROR TYPE:", type(e).__name__)
        print("ERROR MESSAGE:", str(e))
        print("========================================\n")

        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)}",
        )


@app.get("/api/download/{filename}")
def download_pdf(filename: str):
    # Prevent path traversal
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    pdf_path = PDF_DIR / filename

    if not pdf_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"PDF not found: {filename}",
        )

    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type="application/pdf",
    )
