import os
os.environ.pop("SSLKEYLOGFILE", None)
import time
import json
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError


def evaluate_biomarkers(validated_data: dict) -> dict:
    """Clinical rule-engine that translates validated blood report markers into safe training constraints."""
    ctx = validated_data.get("patient_context", {})
    labs = validated_data.get("biomarkers", {})

    sex = (ctx.get("biological_sex") or "Male").capitalize()
    flags = []
    intensity_cap = "High Intensity Allowed (HIIT, Sprints & Heavy Strength OK)"
    recommended_styles = []
    extra_rest_days = 0
    medical_alert = False

    def get_val(*keys):
        for k in keys:
            if k in labs:
                entry = labs[k]
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
        return None

    # Support both DB standard_key and parser.py spelling variants
    hb = get_val("hemoglobin", "haemoglobin")
    ferritin = get_val("ferritin", "serum_ferritin")
    vit_d = get_val("vitamin_d", "25_oh_vitamin_d")
    hba1c = get_val("hba1c", "fasting_glucose")
    tsh = get_val("thyroid_stimulating_hormone", "tsh")
    esr = get_val("erythrocyte_sedimentation_rate", "esr")
    crp = get_val("hs_crp", "crp")
    ck = get_val("creatine_kinase", "ck")
    wbc = get_val("total_leukocyte_count", "wbc_count")
    platelets = get_val("platelet_count", "platelets")

    # 1. Oxygen Carrying Capacity (Hemoglobin & Ferritin)
    hb_min = 13.5 if sex == "Male" else 12.0
    if hb is not None and hb < hb_min:
        flags.append(
            f"Low Hemoglobin ({hb} gm/dL): Reduced oxygen delivery. Avoid exhaustive HIIT and sprints."
        )
        intensity_cap = "Low to Moderate Intensity Only (Zone 2 Cardio & Light Strength)"
        recommended_styles.append("Zone 2 Walking/Cycling")
        if hb < 10.0:
            medical_alert = True
            flags.append("CRITICAL: Severe anemia range. Medical clearance required before exercise.")

    if ferritin is not None and ferritin < 30:
        flags.append(
            f"Low Ferritin ({ferritin} ng/mL): Depleted iron stores. Cap high-impact endurance."
        )
        if "Low" not in intensity_cap:
            intensity_cap = "Moderate Intensity Only (Avoid Exhaustive HIIT)"

    # 2. Systemic Inflammation & Muscle Recovery (ESR, hs-CRP, CK, WBC)
    if (esr is not None and esr > 15) or (crp is not None and crp > 3.0):
        flags.append(
            "Elevated Inflammatory Marker (ESR/hs-CRP): Prioritize active recovery and sleep."
        )
        extra_rest_days += 1
        recommended_styles.append("Mobility & Yoga")

    if ck is not None and ck > 400:
        flags.append(
            f"High Creatine Kinase ({ck} U/L): Residual muscle damage detected. Delay heavy lifting."
        )
        extra_rest_days += 1

    if wbc is not None and (wbc < 4000 or wbc > 11000):
        flags.append(
            f"Out-of-range WBC ({wbc} cells/cu.mm): Possible immune stress. Avoid overtraining."
        )
        extra_rest_days += 1

    # 3. Platelet Safety Check
    if platelets is not None and platelets < 100:
        medical_alert = True
        flags.append(
            f"Low Platelets ({platelets} 10^3/µL): Avoid heavy contact sports and maximal straining."
        )

    # 4. Thyroid, Bone Health & Metabolic Efficiency (TSH, Vitamin D, HbA1c)
    if tsh is not None and tsh > 4.5:
        flags.append(
            f"Elevated TSH ({tsh} µIU/mL): Slower metabolic recovery. Keep sessions under 45 mins."
        )

    if vit_d is not None and vit_d < 20:
        flags.append(
            f"Low Vitamin D ({vit_d} ng/mL): Higher bone stress risk. Avoid high-impact plyometrics."
        )

    if hba1c is not None and hba1c >= 5.7:
        flags.append(
            f"Elevated HbA1c/Glucose ({hba1c}): Prioritize resistance training and post-meal Zone 2 walks."
        )
        recommended_styles.extend(["Hypertrophy / Resistance Training", "Post-Meal Zone 2 Walks"])

    # Nuanced check for relative WBC differential shifts when absolute counts are normal
    lymph_status = labs.get("lymphocytes_percentage", {}).get("status") if isinstance(labs.get("lymphocytes_percentage"), dict) else None
    mono_status = labs.get("monocytes_percentage", {}).get("status") if isinstance(labs.get("monocytes_percentage"), dict) else None
    abs_lymph_status = labs.get("absolute_lymphocyte_count", {}).get("status") if isinstance(labs.get("absolute_lymphocyte_count"), dict) else None

    if (lymph_status == "high" or mono_status == "high") and abs_lymph_status == "normal":
        flags.append(
            "Note: Mild relative Lymphocyte/Monocyte % shift with normal absolute counts and ESR—safe to train, monitor fatigue."
        )

    if not flags:
        flags.append("All tested biomarkers are within optimal ranges for full-intensity training.")

    return {
        "medical_alert": medical_alert,
        "intensity_cap": intensity_cap,
        "extra_rest_days": extra_rest_days,
        "recommended_styles": list(set(recommended_styles)),
        "clinical_flags": flags,
    }


def generate_routine(
    validated_data: dict,
    user_profile: dict,
    model_name: str = "gemini-3.8-flash",
) -> dict:
    """Combines clinical rules with Gemini API to build a structured, personalized workout routine."""
    ctx = validated_data.get("patient_context", {})
    rules = evaluate_biomarkers(validated_data)

    if rules["medical_alert"]:
        return {
            "status": "medical_hold",
            "rules": rules,
            "routine_markdown": "⚠️ **Medical Clearance Required:**\n"
            + "\n".join(f"- {flag}" for flag in rules["clinical_flags"])
            + "\nPlease consult a physician before starting a workout program.",
        }

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not found in environment variables or .env file.")

    client = genai.Client(api_key=api_key)

    missing_tests = user_profile.get("missing_biomarkers", [])
    missing_note = (
        f"- Missing Recommended Tests for Mode: {', '.join(missing_tests)}"
        if missing_tests
        else "- Panel Completeness: All recommended mode biomarkers present"
    )

    prompt = f"""
You are an expert sports physiologist and strength & conditioning coach. Build a safe, personalized weekly workout routine strictly grounded in the patient's validated blood report and training profile below.

PATIENT & TRAINING PROFILE:
- Age: {ctx.get('age')} | Biological Sex: {ctx.get('biological_sex')}
- Training Mode: {user_profile.get('training_mode', 'general_fitness')}
- Primary Goal: {user_profile.get('goal', 'General Fitness')}
- Experience Level: {user_profile.get('experience', 'Intermediate')}
- Available Days/Week: {user_profile.get('days_per_week', 4)}
- Preferred Session Duration: {user_profile.get('duration_mins', 45)} minutes
- Injuries/Conditions: {user_profile.get('conditions', 'None')}

CLINICAL BIOMARKER RULES (MUST STRICTLY OBEY):
- Maximum Allowed Intensity: {rules['intensity_cap']}
- Priority Training Styles: {', '.join(rules['recommended_styles']) or 'Match to user training mode & goal'}
- Extra Rest Days Needed: {rules['extra_rest_days']}
{missing_note}
- Biomarker Findings:
{json.dumps(rules['clinical_flags'], indent=2)}

OUTPUT FORMAT (Markdown):
1. **Biomarker Readiness Summary**: 3 concise bullet points explaining how their specific blood test numbers shape their intensity ceiling and recovery.
2. **Weekly Training Schedule**: Day-by-day workout split matching their available days and session duration (include specific exercises, sets x reps, rest periods, and cardio intensity zones).
3. **Recovery & Nutrition Guidance**: Actionable hydration, sleep, and nutrition tips tailored to their lab profile (and briefly mention any blind spots if key tests were missing).
"""

    models_to_try = list(
        dict.fromkeys(
            [
                model_name,
                "gemini-3.8-flash",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
            ]
        )
    )
    response_text = None

    for current_model in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                    ),
                )
                if response and response.text:
                    response_text = response.text
                    break
            except ServerError as e:
                if e.code == 503:
                    wait_time = 2 ** attempt
                    print(f"   [{current_model}] Server busy (503). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"   [{current_model}] ServerError {e.code}. Switching model...")
                    break
            except ClientError as e:
                print(f"   [{current_model}] ClientError {e.code}. Switching model...")
                break
        if response_text:
            break

    # Offline / High-Demand Safety Net: Fallback to local Ollama on RTX 4050
    if not response_text:
        print("   [Fallback] Gemini API busy (503). Falling back to local Ollama (qwen2.5:3b)...")
        try:
            import ollama
            local_resp = ollama.chat(
                model="qwen2.5:3b",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_ctx": 2048},
            )
            response_text = local_resp["message"]["content"]
        except Exception as ollama_err:
            raise RuntimeError(
                f"Both Gemini API (503) and local Ollama fallback failed: {ollama_err}"
            )

    return {
        "status": "ready",
        "rules": rules,
        "routine_markdown": response_text,
    }
