import os
os.environ.pop("SSLKEYLOGFILE", None)  # Prevents Windows SSL PermissionError
import sys

if __name__ == "__main__" and os.environ.get("STREAMLIT_RUNNING") != "1":
    os.environ["STREAMLIT_RUNNING"] = "1"
    os.execv(sys.executable, [sys.executable, "-m", "streamlit", "run", __file__])

import tempfile
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from ingestion.db_loader import DatabaseLoader, DEFAULT_DB_PATH
from main import run_from_pdf, run_from_existing_report
from engine.gmail_sender import send_routine_via_gmail

st.set_page_config(
    page_title="VeeruFit | Biomarker Workout Engine",
    page_icon="🧬",
    layout="wide",
)


def register_client_in_db(
    db: DatabaseLoader, full_name: str, email: str, training_mode: str, report_id: int
):
    """Saves client registration details in SQLite linked to their report_id."""
    if not email:
        return
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registered_clients (
                client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                email TEXT NOT NULL,
                training_mode TEXT,
                report_id INTEGER,
                registered_at TEXT,
                FOREIGN KEY (report_id) REFERENCES lab_reports (report_id)
            )
        """)
        cursor.execute(
            """
            INSERT INTO registered_clients (full_name, email, training_mode, report_id, registered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                full_name or "Athlete",
                email,
                training_mode,
                report_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


# --- HEADER ---
st.title("🧬 VeeruFit — Biomarker-Driven Personalized Workout Engine")
st.markdown(
    "Upload a blood lab report to analyze **oxygen capacity, inflammation, and metabolic readiness**, "
    "and receive your clinically grounded training PDF directly in your inbox."
)
st.divider()

# --- SIDEBAR: CLIENT REGISTRATION & ONBOARDING ---
with st.sidebar:
    st.header("1. Athlete Registration")

    patient_name_input = st.text_input(
        "Full Name",
        placeholder="e.g., Moshikvarmaa C (overrides PDF name)",
    )

    client_email_input = st.text_input(
        "Client Email ID (for PDF Delivery)",
        placeholder="e.g., client@gmail.com",
    )

    st.divider()
    st.header("2. Training Preferences")

    training_mode = st.selectbox(
        "Training Mode",
        options=[
            "general_fitness",
            "hybrid_athlete",
            "hypertrophy_prep",
            "combat_sports",
            "calisthenics",
        ],
        format_func=lambda x: x.replace("_", " ").title(),
    )

    goal = st.text_input(
        "Primary Fitness Goal",
        value="Athletic Conditioning & Lean Muscle",
    )

    experience = st.selectbox(
        "Experience Level",
        options=["Beginner", "Intermediate", "Advanced"],
        index=1,
    )

    col1, col2 = st.columns(2)
    with col1:
        days_per_week = st.number_input("Days / Week", min_value=2, max_value=6, value=4)
    with col2:
        duration_mins = st.selectbox("Duration (mins)", options=[30, 45, 60, 75, 90], index=2)

    conditions = st.text_area(
        "Injuries or Medical Notes",
        value="None",
        height=70,
    )

    model_choice = st.selectbox(
        "AI Model",
        options=["gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.5-flash-lite"],
        index=0,
    )

# --- MAIN AREA: REPORT INPUT ---
st.subheader("3. Select Blood Report Source")
input_mode = st.radio(
    "Choose how to load lab data:",
    options=["Upload New Blood Report (PDF / Image)", "Load Saved Report from Database"],
    horizontal=True,
)

uploaded_file = None
selected_report_id = None
db = DatabaseLoader(DEFAULT_DB_PATH)

if input_mode == "Upload New Blood Report (PDF / Image)":
    uploaded_file = st.file_uploader(
        "Upload Lab Report (.pdf, .png, .jpg, .jpeg)",
        type=["pdf", "png", "jpg", "jpeg"],
    )
else:
    with db._get_connection() as conn:
        rows = conn.execute(
            "SELECT report_id, patient_name, age, biological_sex, source_file FROM lab_reports ORDER BY report_id DESC"
        ).fetchall()

    if rows:
        report_options = {
            f"ID #{r['report_id']} — {r['patient_name'] or 'Unknown'} ({r['biological_sex']}, Age {r['age']}) [{r['source_file']}]": r["report_id"]
            for r in rows
        }
        chosen_label = st.selectbox("Select Saved Report", options=list(report_options.keys()))
        selected_report_id = report_options[chosen_label]
    else:
        st.warning("No saved reports found in mvp_fitness.db yet. Upload a new PDF above!")

# --- GENERATE & AUTO-EMAIL BUTTON ---
user_profile = {
    "patient_name": patient_name_input.strip(),
    "training_mode": training_mode,
    "goal": goal,
    "experience": experience,
    "days_per_week": int(days_per_week),
    "duration_mins": int(duration_mins),
    "conditions": conditions.strip() or "None",
}

if st.button("🚀 Analyze Biomarkers, Build Routine & Email PDF", type="primary", use_container_width=True):
    try:
        with st.spinner("Extracting biomarkers, validating panel relevance, and building your routine..."):
            if input_mode == "Upload New Blood Report (PDF / Image)":
                if not uploaded_file:
                    st.error("Please upload a PDF or image file first.")
                    st.stop()

                temp_dir = Path(tempfile.mkdtemp())
                temp_file_path = temp_dir / uploaded_file.name
                temp_file_path.write_bytes(uploaded_file.getbuffer())

                output = run_from_pdf(
                    file_path=temp_file_path,
                    user_profile=user_profile,
                    model_name=model_choice,
                )
            else:
                if selected_report_id is None:
                    st.error("Please select a valid report from the database.")
                    st.stop()

                output = run_from_existing_report(
                    report_id=selected_report_id,
                    user_profile=user_profile,
                    model_name=model_choice,
                )

        st.session_state["last_output"] = output
        st.session_state["last_profile"] = user_profile
        st.session_state["last_email"] = client_email_input.strip()
        st.success("✅ Analysis & Personalized Workout Plan Ready!")

        # Automatically send email if client entered an email address
        recipient = client_email_input.strip()
        if recipient:
            register_client_in_db(
                db=db,
                full_name=patient_name_input.strip(),
                email=recipient,
                training_mode=training_mode,
                report_id=output["report_id"],
            )

            pdf_dir = Path(__file__).resolve().parent / "generated_pdfs"
            report_id = output.get("report_id")
            matching_pdfs = sorted(
                pdf_dir.glob(f"*_Report{report_id}_WorkoutPlan.pdf"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if matching_pdfs:
                with st.spinner(f"Sending VeeruFit PDF report to {recipient}..."):
                    sent = send_routine_via_gmail(
                        recipient_email=recipient,
                        patient_name=patient_name_input.strip() or "Athlete",
                        pdf_path=matching_pdfs[0],
                        training_mode=training_mode,
                        intensity_cap=output.get("rules", {}).get("intensity_cap", "Standard"),
                    )
                if sent:
                    st.success(f"📧 VeeruFit PDF report sent to **{recipient}**!")
            else:
                st.warning("Routine generated, but could not locate the exported PDF file to attach.")

    except Exception as e:
        st.error(f"Error: {e}")

# --- DISPLAY RESULTS ---
if "last_output" in st.session_state:
    output = st.session_state["last_output"]
    validation = output.get("validation", {})
    rules = output.get("rules", {})

    st.divider()
    st.subheader("4. Biomarker Readiness & Rationale")

    m1, m2, m3 = st.columns(3)
    m1.metric(
        label="Panel Relevance Score",
        value=f"{validation.get('relevance_percentage', 0)}%",
        delta=validation.get("verdict", "N/A"),
    )
    m2.metric(
        label="Extra Recovery Days",
        value=f"+{rules.get('extra_rest_days', 0)} Days",
    )
    m3.metric(
        label="Report ID",
        value=f"#{output.get('report_id', 'N/A')}",
    )

    st.info(f"**Safe Intensity Ceiling:** {rules.get('intensity_cap', 'Standard')}")

    with st.expander("🔍 Why We Chose This Routine (Clinical Biomarker Findings)", expanded=True):
        for flag in rules.get("clinical_flags", []):
            st.markdown(f"- {flag}")

        missing = validation.get("missing_biomarkers", [])
        if missing:
            st.warning(
                f"**Recommended Follow-Up Tests for `{validation.get('training_mode')}`:** "
                + ", ".join(missing)
            )

    pdf_dir = Path(__file__).resolve().parent / "generated_pdfs"
    report_id = output.get("report_id")
    matching_pdfs = sorted(
        pdf_dir.glob(f"*_Report{report_id}_WorkoutPlan.pdf"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if matching_pdfs:
        latest_pdf = matching_pdfs[0]
        col_dl, col_resend = st.columns(2)

        with col_dl:
            with open(latest_pdf, "rb") as pdf_file:
                st.download_button(
                    label="📄 Download Full PDF Report",
                    data=pdf_file.read(),
                    file_name=latest_pdf.name,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    )
        with col_resend:
            if st.button("📧 Send / Resend PDF to Email", use_container_width=True):
                target_email = client_email_input.strip() or st.session_state.get("last_email", "")
            if not target_email:
                st.warning("Enter a Client Email ID in the sidebar first.")
            else:
                try:
                    send_routine_via_gmail(
                        recipient_email=target_email,
                        patient_name=patient_name_input.strip() or "Athlete",
                        pdf_path=latest_pdf,
                        training_mode=validation.get("training_mode", "general_fitness"),
                        intensity_cap=rules.get("intensity_cap", "Standard"),
                        )
                    st.success(f"📧 Sent {latest_pdf.name} to {target_email}!")
                except Exception as mail_err:
                    st.error(f"Email failed: {mail_err}")
                st.divider()
                st.subheader("5. Your Personalized Weekly Workout Plan")
                st.markdown(output.get("routine_markdown", ""))