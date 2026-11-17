import os
import base64
from pathlib import Path
import requests

os.environ.pop("SSLKEYLOGFILE", None)


def send_routine_via_gmail(
    recipient_email: str,
    patient_name: str,
    pdf_path: str | Path,
    training_mode: str = "general_fitness",
    intensity_cap: str = "Standard",
) -> bool:
    """
    Sends the VeeruFit PDF workout report from your personal Gmail via Google Apps Script.
    """
    webhook_url = os.environ.get("APPS_SCRIPT_EMAIL_URL", "").strip()
    if not webhook_url:
        raise EnvironmentError(
            "APPS_SCRIPT_EMAIL_URL is missing in your .env file. Did you save .env and restart Streamlit?"
        )

    recipient_email = recipient_email.strip()
    if not recipient_email or "@" not in recipient_email:
        raise ValueError(f"Invalid recipient email address: {recipient_email}")

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found for attachment: {pdf_path}")

    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    subject = f"Your Personalized Workout Plan from VeeruFit - {patient_name}"
    body_text = (
        f"Hi {patient_name},\n\n"
        "Welcome to VeeruFit! Your personalized workout routine—built around your unique "
        "blood report biomarkers and fitness goals—is attached to this email as a PDF. "
        "Remember, real transformation doesn't come from one extreme workout; it comes from "
        "showing up consistently, respecting your body's recovery signals, and making small, "
        "disciplined deposits every single week. As the saying goes, \"Success isn't always "
        "about greatness—it's about consistency. Consistent hard work leads to success, and "
        "greatness will come.\" Trust the process, follow your intensity guidelines, and take "
        "it one session at a time.\n\n"
        "Stay strong and consistent,\n"
        "Team VeeruFit\n\n"
        "Disclaimer: This workout routine and biomarker summary are generated for educational "
        "and general fitness guidance only and do not constitute medical advice, diagnosis, "
        "or treatment. Always consult a qualified physician or healthcare professional before "
        "beginning any new exercise program, especially if you have underlying medical "
        "conditions or abnormal lab results.\n"
    )

    payload = {
        "to": recipient_email,
        "subject": subject,
        "body": body_text,
        "filename": pdf_path.name,
        "pdf_base64": pdf_b64,
    }

    resp = requests.post(webhook_url, json=payload, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Apps Script returned HTTP {resp.status_code}: {resp.text[:300]}"
        )

    try:
        result = resp.json()
    except Exception:
        raise RuntimeError(
            f"Apps Script did not return JSON (check that 'Who has access' is set to 'Anyone'). Response: {resp.text[:300]}"
        )

    if result.get("status") != "sent":
        raise RuntimeError(f"Apps Script error: {result}")

    return True
