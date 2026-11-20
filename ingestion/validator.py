from typing import Literal

TrainingMode = Literal[
    "hypertrophy_prep",
    "combat_sports",
    "hybrid_athlete",
    "calisthenics",
    "general_fitness",
]


class ReportValidator:
    """
    Evaluates extracted biomarkers against user onboarding preferences
    to calculate a relevance score (%) and list missing recommended tests.
    """

    # Required/recommended biomarkers per training mode with weights
    MODE_REQUIREMENTS: dict[str, dict[str, int]] = {
        "hypertrophy_prep": {
            "hemoglobin": 15,
            "wbc_count": 10,
            "tsh": 15,
            "testosterone_total": 15,
            "estradiol": 10,
            "ast": 10,
            "alt": 10,
            "creatinine": 15,
        },
        "combat_sports": {
            "hemoglobin": 20,
            "rbc_count": 15,
            "platelets": 15,
            "electrolytes": 15,
            "creatinine": 15,
            "cortisol": 10,
            "vitamin_d": 10,
        },
        "hybrid_athlete": {
            "hemoglobin": 20,
            "rbc_count": 15,
            "ferritin": 20,
            "esr": 10,
            "tsh": 15,
            "vitamin_d": 10,
            "fasting_glucose": 10,
        },
        "calisthenics": {
            "hemoglobin": 20,
            "vitamin_d": 25,
            "calcium": 20,
            "vitamin_b12": 15,
            "esr": 10,
            "tsh": 10,
        },
        "general_fitness": {
            "hemoglobin": 20,
            "wbc_count": 15,
            "platelets": 15,
            "tsh": 20,
            "fasting_glucose": 15,
            "vitamin_d": 15,
        },
    }

    # Maps canonical requirement keys to possible variations extracted by parser.py
    KEY_ALIASES: dict[str, list[str]] = {
        "hemoglobin": ["hemoglobin", "haemoglobin", "hb", "hgb"],
        "rbc_count": ["rbc_count", "erythrocyte_rbc_count", "rbc", "erythrocyte_count"],
        "wbc_count": ["wbc_count", "total_leucocytes_wbc_count", "wbc", "total_wbc"],
        "platelets": ["platelets", "platelet_count", "plt"],
        "tsh": ["tsh", "thyroid_stimulating_hormone", "tsh_ultrasensitive"],
        "esr": ["esr", "erythrocyte_sedimentation_rate"],
        "ferritin": ["ferritin", "serum_ferritin"],
        "vitamin_d": ["vitamin_d", "25_oh_vitamin_d", "vitamin_d_total"],
        "vitamin_b12": ["vitamin_b12", "cyanocobalamin"],
        "fasting_glucose": ["fasting_glucose", "glucose_fasting", "fbs", "hba1c"],
        "testosterone_total": ["testosterone_total", "total_testosterone", "testosterone"],
        "estradiol": ["estradiol", "e2", "serum_estradiol"],
        "ast": ["ast", "sgot", "aspartate_aminotransferase"],
        "alt": ["alt", "sgpt", "alanine_aminotransferase"],
        "creatinine": ["creatinine", "serum_creatinine"],
        "electrolytes": ["electrolytes", "sodium", "potassium"],
        "calcium": ["calcium", "serum_calcium"],
        "cortisol": ["cortisol", "serum_cortisol"],
    }
    def _normalize_key(self, key: str) -> str:
        return (
        key.lower()
        .strip()
        .replace("-", "_")
        .replace(" ", "_")
        )
    def _is_marker_present(self, required_key: str, extracted_keys: set[str]) -> bool:
        aliases = self.KEY_ALIASES.get(required_key, [required_key])

        normalized_aliases = {
        self._normalize_key(alias)
        for alias in aliases
    }

        normalized_extracted = {
        self._normalize_key(key)
        for key in extracted_keys
    }

        return bool(normalized_aliases & normalized_extracted)


    def validate(
        self,
        parsed_data: dict,
        training_mode: TrainingMode = "general_fitness",
        age: float | None = None,
    ) -> dict:
        """
        Evaluates parsed biomarker data against onboarding mode requirements.
        Returns relevance percentage, usability flag, matched tests, and missing tests.
        """
        extracted_biomarkers = parsed_data.get("biomarkers", {})
        extracted_keys = {k.lower() for k in extracted_biomarkers.keys()}

        # Use age from report if not explicitly passed from onboarding
        patient_age = age or parsed_data.get("patient_context", {}).get("age")

        requirements = self.MODE_REQUIREMENTS.get(
            training_mode, self.MODE_REQUIREMENTS["general_fitness"]
        ).copy()

        # Add age-specific check for 30+ users
        if patient_age and patient_age >= 30 and "fasting_glucose" not in requirements:
            requirements["fasting_glucose"] = 10

        total_weight = sum(requirements.values())
        matched_weight = 0
        matched_tests = []
        missing_tests = []

        for req_key, weight in requirements.items():
            if self._is_marker_present(req_key, extracted_keys):
                matched_weight += weight
                matched_tests.append(req_key)
            else:
                missing_tests.append(req_key)

        relevance_percentage = round((matched_weight / total_weight) * 100, 1)

        # Usability decision logic for MVP demo
        if relevance_percentage >= 75:
            verdict = "Optimal Match"
            usable = True
            message = "Report covers all core and mode-specific biomarkers needed for high-precision programming."
        elif relevance_percentage >= 45:
            verdict = "Usable (Partial Panel)"
            usable = True
            message = (
                f"Report covers {relevance_percentage}% of recommended markers. "
                "Usable for safe baseline programming, though uploading missing tests will unlock deeper insights."
            )
        else:
            verdict = "Insufficient Relevance"
            usable = False
            message = (
                f"Only {relevance_percentage}% relevant for '{training_mode}'. "
                "Please upload a blood panel containing the missing core biomarkers."
            )

        return {
            "training_mode": training_mode,
            "relevance_percentage": relevance_percentage,
            "usable": usable,
            "verdict": verdict,
            "message": message,
            "matched_biomarkers": matched_tests,
            "missing_biomarkers": missing_tests,
        }
