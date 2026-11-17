import re
from pathlib import Path
from datetime import datetime
from fpdf import FPDF


class WorkoutPDFReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(30, 58, 138)
        self.cell(
            0,
            10,
            "Personalized Biomarker-Driven Workout Plan",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            10,
            f"Generated on {datetime.now().strftime('%Y-%m-%d')} | Educational fitness guidance only - consult a physician before starting.",
            align="C",
        )


def _clean_text(text: str) -> str:
    """Strips Markdown symbols and normalizes Unicode characters for standard PDF fonts."""
    text = text.replace("**", "").replace("### ", "").replace("## ", "").replace("# ", "")
    replacements = {
        "µ": "u",
        "–": "-",
        "—": "-",
        "’": "'",
        "“": '"',
        "”": '"',
        "•": "-",
        "⚠️": "[ALERT]",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def _write_wrapped(pdf: FPDF, height: float, text: str):
    """Safely writes a full-width wrapped block by resetting X to the left margin first."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        w=pdf.epw,
        h=height,
        text=text,
        new_x="LMARGIN",
        new_y="NEXT",
    )


def export_routine_to_pdf(
    output_dir: str | Path,
    parsed_data: dict,
    user_profile: dict,
    pipeline_output: dict,
) -> Path:
    """Builds a clean PDF containing patient context, biomarker rationale, and weekly routine."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ctx = parsed_data.get("patient_context", {})
    patient_name = ctx.get("patient_name") or "Athlete"
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", patient_name).strip("_")
    report_id = pipeline_output.get("report_id", "0")
    pdf_path = output_dir / f"{safe_name}_Report{report_id}_WorkoutPlan.pdf"

    pdf = WorkoutPDFReport()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Section 1: Patient & Onboarding Profile
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    _write_wrapped(pdf, 8, "1. Athlete & Training Profile")

    pdf.set_font("Helvetica", "", 10)
    profile_lines = [
        f"Name: {_clean_text(str(patient_name))}   |   Age: {ctx.get('age', 'N/A')}   |   Sex: {ctx.get('biological_sex', 'N/A')}",
        f"Training Mode: {user_profile.get('training_mode', 'general_fitness')}   |   Goal: {_clean_text(str(user_profile.get('goal', 'General Fitness')))}",
        f"Schedule: {user_profile.get('days_per_week', 4)} Days/Week   |   Duration: {user_profile.get('duration_mins', 45)} mins/session",
    ]
    for line in profile_lines:
        _write_wrapped(pdf, 6, line)
    pdf.ln(3)

    # Section 2: Blood Panel Relevance & Clinical Rationale
    validation = pipeline_output.get("validation", {})
    rules = pipeline_output.get("rules", {})

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 58, 138)
    _write_wrapped(pdf, 8, "2. Why We Chose This Routine (Biomarker Analysis)")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 20, 20)
    _write_wrapped(
        pdf,
        6,
        _clean_text(
            f"Panel Match: {validation.get('verdict', 'N/A')} ({validation.get('relevance_percentage', 0)}%)"
        ),
    )
    _write_wrapped(
        pdf,
        6,
        _clean_text(f"Safe Intensity Ceiling: {rules.get('intensity_cap', 'Standard')}"),
    )

    pdf.set_font("Helvetica", "", 10)
    for flag in rules.get("clinical_flags", []):
        _write_wrapped(pdf, 6, _clean_text(f"  - {flag}"))

    missing = validation.get("missing_biomarkers", [])
    if missing:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(90, 90, 90)
        _write_wrapped(
            pdf,
            6,
            _clean_text(
                f"  Note - Recommended follow-up tests for deeper tracking: {', '.join(missing)}"
            ),
        )
    pdf.ln(4)

    # Section 3: Personalized Weekly Routine
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 58, 138)
    _write_wrapped(pdf, 8, "3. Personalized Weekly Workout Routine")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(20, 20, 20)
    routine_text = _clean_text(pipeline_output.get("routine_markdown", ""))

    for raw_line in routine_text.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(3)
            continue
        if re.match(r"^(Day\s*\d+|1\.|2\.|3\.)", line, re.IGNORECASE):
            pdf.set_font("Helvetica", "B", 10)
            _write_wrapped(pdf, 6, line)
            pdf.set_font("Helvetica", "", 10)
        else:
            _write_wrapped(pdf, 5.5, line)

    pdf.output(str(pdf_path))
    return pdf_path
class WorkoutPDFReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 58, 138)  # Deep Navy
        self.cell(
            0,
            8,
            "VEERUFIT | Biomarker-Driven Personalized Workout Plan",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(
            0,
            5,
            "Precision Training Built Around Your Biology",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(30, 58, 138)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            10,
            f"Team VeeruFit | Generated {datetime.now().strftime('%Y-%m-%d')} | Educational fitness guidance only - consult a physician before starting.",
            align="C",
        )
