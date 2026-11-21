import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Activity,
  Upload,
  Mail,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Dumbbell,
  FlaskConical,
  ShieldCheck,
  Loader2,
  Download,
} from "lucide-react";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV
    ? "http://localhost:8000"
    : "https://veerufit-varmaa.onrender.com");


export default function App() {
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    training_mode: "general_fitness",
    goal: "Athletic Conditioning, Stamina & Lean Muscle",
    experience: "Intermediate",
    days_per_week: 4,
    duration_mins: 60,
    conditions: "None",
  });

  const [reportFile, setReportFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState("routine");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    const selected = e.target.files && e.target.files[0];
    if (selected) {
      setReportFile(selected);
      setError("");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!formData.full_name.trim()) {
      setError("Please enter the athlete's full name.");
      return;
    }
    if (!reportFile) {
      setError("Please upload a blood lab report (PDF or Image).");
      return;
    }

    setLoading(true);
    try {
      const payload = new FormData();
      Object.entries(formData).forEach(([key, val]) => {
        payload.append(key, val);
      });
      payload.append("report_file", reportFile);

      const response = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        body: payload,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to process blood report.");
      }

      setResult(data);
      setActiveTab("routine");
    } catch (err) {
      setError(
        err.message ||
          "Could not connect to VeeruFit backend API. Make sure uvicorn api:app is running on port 8000."
      );
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || "normal").toLowerCase();
    if (s === "high" || s === "low") {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
          {s}
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
        {s}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center">
            <img
            src="/VeeruFit-logo.png"
            alt="VeeruFit - Form. Focus. Fight."
            className="h-12 w-auto object-contain"
            />
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            <ShieldCheck className="w-4 h-4 text-teal-400" />
            Clinical Guardrails Active
          </span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Hero Banner */}
        <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 border border-blue-800/40 p-7 mb-8 shadow-xl">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">
            Train Smarter With Your Blood Biomarkers
          </h2>
          <p className="text-slate-300 text-sm sm:text-base max-w-3xl">
            Register your details and upload your blood lab report to receive a
            personalized workout routine PDF calibrated to your biology.
          </p>
        </div>

        {/* Main Form */}
        <form
          onSubmit={handleSubmit}
          className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-10"
        >
          {/* Step 1: Client Details */}
          <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
            <h3 className="text-sm font-bold uppercase tracking-wider text-teal-400 mb-4">
              Step 1 · Athlete Registration & Goals
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Full Name *
                </label>
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  placeholder="e.g., athelete name"
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Email ID
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="athlete@gmail.com"
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 pl-10 pr-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Training Discipline
                </label>
                <select
                  name="training_mode"
                  value={formData.training_mode}
                  onChange={handleChange}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
                >
                  <option value="general_fitness">General Fitness</option>
                  <option value="hybrid_athlete">Hybrid Athlete</option>
                  <option value="hypertrophy_prep">Hypertrophy Prep</option>
                  <option value="combat_sports">Combat Sports</option>
                  <option value="calisthenics">Calisthenics</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Experience Level
                </label>
                <select
                  name="experience"
                  value={formData.experience}
                  onChange={handleChange}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
                >
                  <option value="Beginner">Beginner</option>
                  <option value="Intermediate">Intermediate</option>
                  <option value="Advanced">Advanced</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Days / Week:{" "}
                  <span className="text-white">{formData.days_per_week}</span>
                </label>
                <input
                  type="range"
                  name="days_per_week"
                  min="2"
                  max="6"
                  value={formData.days_per_week}
                  onChange={handleChange}
                  className="w-full accent-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Session Duration (Mins)
                </label>
                <select
                  name="duration_mins"
                  value={formData.duration_mins}
                  onChange={handleChange}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
                >
                  <option value={30}>30 Mins</option>
                  <option value={45}>45 Mins</option>
                  <option value={60}>60 Mins</option>
                  <option value={75}>75 Mins</option>
                  <option value={90}>90 Mins</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Primary Fitness Goal
                </label>
                <input
                  type="text"
                  name="goal"
                  value={formData.goal}
                  onChange={handleChange}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              {/* Medical Notes */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Injuries / Medical Notes
                </label>
                <input
                  type="text"
                  name="conditions"
                  value={formData.conditions}
                  onChange={handleChange}
                  placeholder="None"
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
                />
              </div>
            </div>
          </div>

          {/* Step 2: File Upload & Submit */}
          <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
            <h3 className="text-sm font-bold uppercase tracking-wider text-teal-400 mb-4">
                Upload Blood Lab Report
            </h3>

            <label className="flex flex-col items-center justify-center w-full min-h-48 border-2 border-dashed border-slate-700 rounded-2xl bg-slate-950/70 hover:border-teal-500 transition cursor-pointer p-6 text-center">
              <Upload className="w-9 h-9 text-teal-400 mb-3" />
              <span className="text-sm font-semibold text-white mb-2">
                {reportFile
                  ? `Selected: ${reportFile.name}`
                  : "Choose your Blood Report PDF or Image"}
              </span>
              <span className="text-xs text-slate-500">
                Supports .PDF, .PNG, .JPG (CBC, Ferritin, TSH, Vitamin D, HbA1c)
              </span>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>

            {error && (
              <div className="mt-4 flex items-start gap-2 rounded-xl bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-300">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-5 flex items-center justify-center gap-2 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-3 text-sm font-bold text-slate-950 transition"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing Biomarkers & Building Plan...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  Generate VeeruFit Plan & Email PDF
                </>
              )}
            </button>
          </div>
        </form>

        {/* Results Dashboard */}
        {result && (
          <section className="mt-10 space-y-6">
            {/* PDF Delivery Banner */}
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-lg font-bold text-white">
                      Personalized Workout Plan Generated (Report #{result.report_id})
                    </h3>
                  </div>
                  <p className="text-sm text-slate-300">
                    {result.email_sent
                      ? `Official PDF emailed to ${formData.email}`
                      : "Your PDF report is ready for download below."}
                  </p>
                </div>

                {result.pdf_filename && (
                  <a
                    href={`${API_BASE}/api/download/${encodeURIComponent(result.pdf_filename)}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition"
                  >
                    <Download className="w-4 h-4" />
                    Download Official PDF
                  </a>
                )}
              </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-center gap-2 text-slate-400 mb-3">
                  <FlaskConical className="w-4 h-4 text-teal-400" />
                  <span className="text-xs font-semibold uppercase">
                    Panel Relevance Score
                  </span>
                </div>
                <p className="text-2xl font-extrabold text-white">
                  {result.validation?.relevance_percentage ?? "N/A"}%
                </p>
                <p className="text-xs text-teal-400 mt-1">
                  · {result.validation?.verdict ?? "Not available"}
                </p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-center gap-2 text-slate-400 mb-3">
                  <ShieldCheck className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-semibold uppercase">
                    Safe Intensity Ceiling
                  </span>
                </div>
                <p className="text-xl font-extrabold text-white">
                  {result.rules?.intensity_cap ?? "Not specified"}
                </p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-center gap-2 text-slate-400 mb-3">
                  <Activity className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-semibold uppercase">
                    Extra Recovery Buffer
                  </span>
                </div>
                <p className="text-2xl font-extrabold text-white">
                  +{result.rules?.extra_rest_days ?? 0}
                </p>
                <p className="text-xs text-slate-400 mt-1">Days / Week</p>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setActiveTab("routine")}
                className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition cursor-pointer ${
                  activeTab === "routine"
                    ? "bg-teal-500 text-slate-950"
                    : "bg-slate-900 text-slate-300 hover:bg-slate-800"
                }`}
              >
                <Dumbbell className="w-4 h-4" />
                Weekly Workout Plan
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("rationale")}
                className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition cursor-pointer ${
                  activeTab === "rationale"
                    ? "bg-teal-500 text-slate-950"
                    : "bg-slate-900 text-slate-300 hover:bg-slate-800"
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                Why We Chose This
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("labs")}
                className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition cursor-pointer ${
                  activeTab === "labs"
                    ? "bg-teal-500 text-slate-950"
                    : "bg-slate-900 text-slate-300 hover:bg-slate-800"
                }`}
              >
                <FlaskConical className="w-4 h-4" />
                Extracted Lab Report
              </button>
            </div>

            {/* Tab Content */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              {/* Workout Routine */}
              {activeTab === "routine" && (
                <div className="prose prose-invert max-w-none prose-headings:text-teal-400 prose-strong:text-white">
                  <ReactMarkdown>
                    {result.routine_markdown || "No workout routine was returned."}
                  </ReactMarkdown>
                </div>
              )}

              {/* Clinical Rationale */}
              {activeTab === "rationale" && (
                <div className="space-y-5">
                  <h3 className="text-lg font-bold text-white">
                    Clinical Biomarker Guardrails Applied
                  </h3>

                  <ul className="space-y-3">
                    {(result.rules?.clinical_flags || []).map((flag, idx) => (
                      <li
                        key={`${idx}-${flag}`}
                        className="flex items-start gap-2 text-sm text-slate-300"
                      >
                        <ShieldCheck className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
                        {flag}
                      </li>
                    ))}
                  </ul>

                  {(result.validation?.missing_biomarkers || []).length > 0 && (
                    <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-4">
                      <p className="text-sm font-bold text-amber-300 mb-2">
                        Recommended Follow-Up Biomarkers:
                      </p>
                      <p className="text-sm text-slate-300">
                        {result.validation.missing_biomarkers.join(", ")}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Extracted Lab Report */}
              {activeTab === "labs" && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs uppercase text-slate-400 border-b border-slate-700">
                      <tr>
                        <th className="px-4 py-3">Biomarker</th>
                        <th className="px-4 py-3">Value</th>
                        <th className="px-4 py-3">Reference Range</th>
                        <th className="px-4 py-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {Object.entries(result.biomarkers || {}).map(([key, item]) => (
                        <tr key={key}>
                          <td className="px-4 py-3 font-semibold text-white">
                            {item.raw_test_name || key}
                          </td>
                          <td className="px-4 py-3 text-slate-300">
                            {item.value} {item.unit}
                          </td>
                          <td className="px-4 py-3 text-slate-400">
                            {item.reference_range || "N/A"}
                          </td>
                          <td className="px-4 py-3">
                            {getStatusBadge(item.status)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
