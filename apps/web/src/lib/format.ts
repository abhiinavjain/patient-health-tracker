import type { Band } from "./types";

const dateFmt = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const monthFmt = new Intl.DateTimeFormat("en-IN", { month: "short", year: "2-digit" });

export const formatDate = (iso: string | null | undefined) => (iso ? dateFmt.format(new Date(iso)) : "—");
export const formatDateTime = (iso: string | null | undefined) => (iso ? dateTimeFmt.format(new Date(iso)) : "—");
export const formatMonth = (ym: string) => monthFmt.format(new Date(`${ym}-01T00:00:00`));
export const pct = (v: number | null | undefined, digits = 0) => (v == null ? "—" : `${(v * 100).toFixed(digits)}%`);

export function relative(iso: string | null | undefined): string {
  if (!iso) return "never";
  const days = Math.round((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days < 0) return days === -1 ? "tomorrow" : `in ${-days} days`;
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  if (days < 365) return `${Math.round(days / 30)} mo ago`;
  return `${(days / 365).toFixed(1)} yr ago`;
}

export const initials = (name: string) =>
  name.replace(/^dr\.?\s+/i, "").split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");

export const titleCase = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const BAND_LABEL: Record<Band, string> = { low: "Low", moderate: "Moderate", high: "High" };
export const BAND_CLASS: Record<Band, string> = {
  low: "bg-risk-low-soft text-risk-low border-risk-low/30",
  moderate: "bg-risk-moderate-soft text-risk-moderate border-risk-moderate/30",
  high: "bg-risk-high-soft text-risk-high border-risk-high/30",
};
export const BAND_BAR: Record<Band, string> = { low: "bg-risk-low", moderate: "bg-risk-moderate", high: "bg-risk-high" };

export const MODEL_SHORT: Record<string, string> = {
  readmission_30d: "Readmission",
  diabetes_risk: "Diabetes",
  cvd_risk: "Heart disease",
};

// Mirror of the API's observation catalog (apps/api/app/catalog.py), for forms and charts.
export const OBSERVATIONS: Record<string, { label: string; unit: string; group: "vital" | "lab" }> = {
  bp_systolic: { label: "Systolic BP", unit: "mmHg", group: "vital" },
  bp_diastolic: { label: "Diastolic BP", unit: "mmHg", group: "vital" },
  heart_rate: { label: "Heart rate", unit: "bpm", group: "vital" },
  respiratory_rate: { label: "Respiratory rate", unit: "breaths/min", group: "vital" },
  spo2: { label: "SpO₂", unit: "%", group: "vital" },
  temperature: { label: "Temperature", unit: "°C", group: "vital" },
  weight: { label: "Weight", unit: "kg", group: "vital" },
  height: { label: "Height", unit: "cm", group: "vital" },
  bmi: { label: "BMI", unit: "kg/m2", group: "vital" },
  hba1c: { label: "HbA1c", unit: "%", group: "lab" },
  glucose_fasting: { label: "Fasting glucose", unit: "mg/dL", group: "lab" },
  glucose_random: { label: "Random glucose", unit: "mg/dL", group: "lab" },
  glucose_postprandial: { label: "Post-meal glucose (2 h)", unit: "mg/dL", group: "lab" },
  cholesterol_total: { label: "Total cholesterol", unit: "mg/dL", group: "lab" },
  ldl: { label: "LDL", unit: "mg/dL", group: "lab" },
  hdl: { label: "HDL", unit: "mg/dL", group: "lab" },
  triglycerides: { label: "Triglycerides", unit: "mg/dL", group: "lab" },
  creatinine: { label: "Creatinine", unit: "mg/dL", group: "lab" },
  egfr: { label: "eGFR", unit: "mL/min/1.73m2", group: "lab" },
  hemoglobin: { label: "Hemoglobin", unit: "g/dL", group: "lab" },
};

// Reference ranges for highlighting out-of-range values (adult, simplified).
export const REFERENCE: Record<string, [number, number]> = {
  bp_systolic: [90, 139], bp_diastolic: [60, 89], heart_rate: [50, 100], respiratory_rate: [12, 20], spo2: [94, 100], temperature: [36.1, 37.5],
  bmi: [18.5, 24.9], hba1c: [4, 5.6], glucose_fasting: [70, 99], glucose_postprandial: [70, 139], cholesterol_total: [0, 199], ldl: [0, 129],
  hdl: [40, 200], triglycerides: [0, 149], creatinine: [0.6, 1.3], egfr: [60, 200], hemoglobin: [12, 17.5],
};

export function outOfRange(code: string, value: number): "high" | "low" | null {
  const r = REFERENCE[code];
  if (!r) return null;
  if (value > r[1]) return "high";
  if (value < r[0]) return "low";
  return null;
}
