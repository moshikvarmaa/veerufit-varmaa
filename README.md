# 🧬 VeeruFit — Biomarker-Driven Personalized Workout Engine (v1)

**VeeruFit** is a full-stack clinical fitness platform that transforms raw blood test reports (PDF or image) into safe, personalized weekly workout routines. Instead of generic fitness templates, VeeruFit analyzes oxygen-carrying capacity, systemic inflammation, and metabolic markers to enforce deterministic safety guardrails before generating an AI-tailored training plan.

---

### 🚀 Key Features (v1)
* **Automated Lab Report Ingestion:** Extracts text from digital PDFs (`pdfplumber`) and scanned lab images (`Tesseract OCR`), parsing biomarkers into standardized JSON via Gemini AI with an offline regex safety net.
* **Training Mode Relevance Validator:** Evaluates lab panels against specific athletic disciplines (*General Fitness, Hybrid Athlete, Hypertrophy Prep, Combat Sports, Calisthenics*) and flags missing recommended biomarkers.
* **Clinical Rule & Safety Engine:** Enforces deterministic sports-physiology guardrails (e.g., capping HIIT when Hemoglobin or Ferritin is low, adding recovery buffers when ESR/WBC indicates stress) before LLM routine generation.
* **Branded PDF Report Exporter:** Generates a clean, downloadable PDF containing the athlete's profile, clinical rationale ("Why We Chose This"), and day-by-day workout split.
* **Automated Email Delivery:** Sends the generated PDF report directly to the registered client's inbox via a Google Apps Script webhook.
* **Modern Full-Stack UI:** Built with **React + Vite + Tailwind CSS** backed by a **FastAPI** REST server and **SQLite** database.

---

### 🏗️ Architecture & Tech Stack
* **Frontend:** React.js, Vite, Tailwind CSS, Lucide Icons, React Markdown
* **Backend API:** Python 3.11, FastAPI, Uvicorn, Pydantic
* **AI & Document Processing:** Google Gemini API (`google-genai`), `pdfplumber`, `pytesseract`, `fpdf2`
* **Database & Automation:** SQLite (`mvp_fitness.db`), Google Apps Script Email Webhook

---

### 📂 Project Structure
```text
veerufit-varmaa/
├── ingestion/               # PDF/OCR extraction, LLM JSON parsing, validation & SQLite loader
│   ├── extractor.py
│   ├── parser.py
│   ├── validator.py
│   └── db_loader.py
├── engine/                  # Biomarker rule engine, PDF exporter & Gmail delivery
│   ├── routine_engine.py
│   ├── pdf_exporter.py
│   └── gmail_sender.py
├── frontend/                # React + Tailwind CSS web dashboard
│   └── src/App.jsx
├── api.py                   # FastAPI REST endpoints (/api/generate, /api/download)
├── main.py                  # Core pipeline orchestrator
└── requirements.txt         # Python dependencies
```

---

### ⚙️ Local Setup & Run

#### 1. Backend Setup (FastAPI)
```bash
pip install -r requirements.txt
```
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key
APPS_SCRIPT_EMAIL_URL=your_google_apps_script_web_app_url
```
Start the API server:
```bash
uvicorn api:app --reload --port 8000
```

#### 2. Frontend Setup (React)
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

### 🗺️ Roadmap
* **v1 (Current):** Blood report ingestion, clinical rule engine, AI routine generation, branded PDF export & email delivery.
* **v2 (Upcoming):** Locality-based nutrition engine (South Indian & regional meal plans calibrated to biomarkers).
* **v3 (Planned):** Mobile application with real-time on-device AI posture & exercise form correction (MediaPipe).

---

### ⚠️ Disclaimer
*VeeruFit provides educational fitness and wellness guidance only and does not constitute medical advice, diagnosis, or treatment. Always consult a qualified physician before starting a new exercise program.*
