import os
import re
import time
import json
from typing import Optional, Literal
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError


class PatientContext(BaseModel):
    patient_name: Optional[str] = Field(description="Full name of the patient")
    age: Optional[float] = Field(description="Age in years as a number")
    biological_sex: Optional[Literal["Male", "Female", "Other"]] = Field(
        description="Biological sex of the patient"
    )


class BiomarkerItem(BaseModel):
    standard_key: str = Field(
        description="Clean snake_case key (e.g., 'hemoglobin', 'tsh', 'vitamin_d', 'wbc_count')"
    )
    raw_test_name: str = Field(description="Exact test name printed on the report")
    value: float = Field(description="Numeric observed value")
    unit: Optional[str] = Field(description="Measurement unit (e.g., 'gm/dL', 'µIU/mL')")
    reference_range: Optional[str] = Field(description="Biological reference interval")
    status: Literal["low", "normal", "high", "unknown"] = Field(
        description="Comparison of observed value against the reference interval"
    )


class LabReportExtraction(BaseModel):
    patient_context: PatientContext
    biomarkers: list[BiomarkerItem] = Field(
        description="All completed numeric lab test results found in the report. Exclude pending tests."
    )


def _offline_fallback_parser(raw_text: str) -> dict:
    """Emergency local regex parser if Gemini API returns 503 during a live demo."""
    print("   [Fallback] Using offline regex parser due to Gemini API high demand...")
    name_match = re.search(r"Name\s*:\s*([^\n]+)", raw_text)
    age_sex_match = re.search(
        r"Age\s*/\s*Gender\s*:\s*([0-9.]+)\s*Year\(s\)\s*/\s*(\w+)",
        raw_text,
        re.IGNORECASE,
    )

    patient_context = {
        "patient_name": name_match.group(1).strip().split("   ")[0] if name_match else None,
        "age": float(age_sex_match.group(1)) if age_sex_match else None,
        "biological_sex": age_sex_match.group(2).strip() if age_sex_match else None,
    }

    # Generic row matcher for layout-preserved PDF text
    row_pattern = re.compile(
        r"^\s*([A-Za-z][A-Za-z0-9\s(),./-]+?)\s{2,}"
        r"([0-9]+(?:\.[0-9]+)?)\s+"
        r"([a-zA-Zµ/%^0-9./-]+(?:\s*/[a-zA-Zµ]+)?)\s+"
        r"([0-9.]+\s*-\s*[0-9.]+)",
        re.MULTILINE,
    )

    biomarkers = {}
    for match in row_pattern.finditer(raw_text):
        raw_test, val, unit, ref_range = match.groups()
        clean_name = re.sub(r"\s+", " ", raw_test).strip()
        key = re.sub(r"[^a-z0-9]+", "_", clean_name.lower()).strip("_")
        # Normalize common hemoglobin key
        if "haemoglobin" in key or "hemoglobin" in key:
            if "mch" not in key:
                key = "hemoglobin"

        low, high = map(float, re.split(r"\s*-\s*", ref_range))
        num_val = float(val)
        status = "low" if num_val < low else ("high" if num_val > high else "normal")

        biomarkers[key] = {
            "raw_test_name": clean_name,
            "value": num_val,
            "unit": unit.strip(),
            "reference_range": ref_range.strip(),
            "status": status,
        }

    return {"patient_context": patient_context, "biomarkers": biomarkers}


def parse_biomarkers_with_llm(raw_text: str) -> dict:
    """Converts raw report text into structured biomarkers with retry, fallback models, and offline safety net."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _offline_fallback_parser(raw_text)

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are a clinical data extraction engine for a personalized fitness and recovery platform.
    Extract the patient details and every completed numeric lab biomarker from the medical report below.
    
    Rules:
    - Do NOT confuse Hemoglobin (Hb) with MCH or MCHC.
    - Ignore tests marked as 'Pending'.
    - Normalize 'standard_key' into clean snake_case suitable for a fitness database.
    - Determine 'status' ('low', 'normal', 'high') strictly by comparing 'value' to 'reference_range'.
    
    Medical Report Text:
    {raw_text}
    """

    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    response = None

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LabReportExtraction,
                    temperature=0.0,
                ),
            )
                break
            except ServerError as e:
                if e.code == 503 and attempt == 0:
                    print(f"[{model_name}] Temporary overload. Retrying once...")
                    time.sleep(2)
                    continue
                print(f"[{model_name}] Failed with server error: {e}")
                break
            except ClientError as e:
                print(f"[{model_name}] API error: {e}")
                break
        if response:
            break

    # If all Gemini models are overloaded (503), use the offline regex parser instead of crashing
    if not response:
        return _offline_fallback_parser(raw_text)

    parsed = json.loads(response.text)
    biomarker_dict = {
        item.pop("standard_key"): item for item in parsed["biomarkers"]
    }

    return {
        "patient_context": parsed["patient_context"],
        "biomarkers": biomarker_dict,
    }
