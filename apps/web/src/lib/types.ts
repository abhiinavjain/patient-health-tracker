// Mirrors the FastAPI response schemas (apps/api/app/schemas.py).

export type Role = "patient" | "clinician" | "admin";
export type Band = "low" | "moderate" | "high";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  specialty: string | null;
  is_active: boolean;
  patient_id: string | null;
}

export interface Clinician {
  id: string;
  full_name: string;
  specialty: string | null;
}

export interface Patient {
  id: string;
  mrn: string;
  full_name: string;
  date_of_birth: string;
  sex: "female" | "male" | "other";
  blood_group: string | null;
  phone: string | null;
  address: string | null;
  emergency_contact: string | null;
  created_at: string;
  age: number | null;
}

export interface PatientListItem {
  id: string;
  mrn: string;
  full_name: string;
  date_of_birth: string;
  sex: Patient["sex"];
  age: number | null;
  last_encounter_at: string | null;
  latest_risk: Record<string, Band>;
}

export interface Condition {
  id: string;
  encounter_id: string | null;
  icd10_code: string;
  description: string;
  status: "active" | "resolved";
  category: "problem" | "encounter";
  is_primary: boolean;
  onset_date: string | null;
  resolved_date: string | null;
  created_at: string;
}

export interface Medication {
  id: string;
  encounter_id: string | null;
  name: string;
  dose: string | null;
  frequency: string | null;
  route: string | null;
  start_date: string | null;
  end_date: string | null;
  status: "active" | "stopped";
  action: string;
}

export interface Allergy {
  id: string;
  substance: string;
  reaction: string | null;
  severity: "mild" | "moderate" | "severe";
  created_at: string;
}

export interface Observation {
  id: string;
  encounter_id: string | null;
  code: string;
  value: number;
  unit: string;
  observed_at: string;
  source: string;
}

export interface LatestObservation {
  code: string;
  label: string;
  value: number;
  unit: string;
  observed_at: string;
}

export interface Appointment {
  id: string;
  patient_id: string;
  clinician: Clinician;
  starts_at: string;
  reason: string | null;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
}

export interface EncounterSummary {
  id: string;
  type: string;
  started_at: string;
  ended_at: string | null;
  reason: string | null;
  clinician: Clinician | null;
  diagnoses: string[];
}

export interface Encounter {
  id: string;
  type: string;
  started_at: string;
  ended_at: string | null;
  reason: string | null;
  notes: string | null;
  admission_type: string | null;
  admission_source: string | null;
  discharge_disposition: string | null;
  procedure_count: number;
  follow_up_date: string | null;
  clinician: Clinician | null;
  conditions: Condition[];
  observations: Observation[];
  medications: Medication[];
}

export interface PatientSummary {
  patient: Patient;
  active_conditions: Condition[];
  active_medications: Medication[];
  allergies: Allergy[];
  latest_observations: LatestObservation[];
  last_encounter: EncounterSummary | null;
  upcoming_appointments: Appointment[];
  encounter_count: number;
}

export interface TimelineEvent {
  at: string;
  kind: "encounter" | "condition" | "medication" | "observation" | "allergy" | "risk";
  title: string;
  detail: string | null;
  encounter_id: string | null;
  ref_id: string | null;
}

export interface ObservationSeries {
  code: string;
  label: string;
  unit: string;
  points: { observed_at: string; value: number; source: string }[];
}

export interface RiskFactor {
  feature: string;
  label: string;
  display_value: string;
  direction: "increases" | "decreases";
  impact: number;
}

export interface RiskResult {
  model: string;
  title: string;
  status: "scored" | "not_applicable" | "insufficient_data";
  reason: string | null;
  model_version: string | null;
  score: number | null;
  band: Band | null;
  percentile: number | null;
  completeness: number | null;
  factors: RiskFactor[];
  missing_inputs: string[];
  computed_at: string | null;
  encounter_id: string | null;
}

export interface RiskModelInfo {
  name: string;
  title: string;
  version: string;
  trained_at: string;
  target: string;
  intended_use: string;
  limitations: string[];
  metrics: { roc_auc: number; roc_auc_ci95: [number, number]; pr_auc: number; brier: number; prevalence: number };
  risk_bands: { moderate: number; high: number };
  top_k: { fraction_flagged: number; precision: number; recall: number; lift: number }[];
}

export interface WorklistRow {
  patient_id: string;
  patient_name: string | null;
  model: string;
  score: number;
  band: Band;
  percentile: number;
  computed_at: string;
  top_factor: string | null;
}

export interface Grant {
  id: string;
  clinician: Clinician;
  granted_at: string;
  revoked_at: string | null;
}

export interface AuditEntry {
  at: string;
  actor_name: string | null;
  actor_role: string | null;
  action: string;
  patient_id: string | null;
  entity: string | null;
  entity_id: string | null;
}

export interface Lifestyle {
  id?: string;
  recorded_at?: string;
  smoker: boolean | null;
  phys_activity: boolean | null;
  fruits_daily: boolean | null;
  veggies_daily: boolean | null;
  heavy_alcohol: boolean | null;
  general_health: number | null;
  poor_mental_health_days: number | null;
  poor_physical_health_days: number | null;
  difficulty_walking: boolean | null;
}

export interface Overview {
  scope: "population" | "my_patients";
  totals: { patients: number; encounters: number; inpatient_stays: number };
  encounters_by_month: { month: string; outpatient: number; inpatient: number; emergency: number; telehealth: number }[];
  readmissions_by_month: { month: string; discharges: number; readmitted_30d: number; rate: number | null }[];
  risk_bands: Record<string, Record<Band, number>>;
  top_conditions: { icd10_code: string; description: string; patients: number }[];
  age_bands: Record<string, number>;
  sex: Record<string, number>;
}

export interface ModelMonitor {
  model: string;
  title: string;
  version: string;
  live_scores: number;
  live_mean_score: number | null;
  reference_mean_score: number;
  psi: number | null;
  drift: "stable" | "moderate" | "significant" | null;
  test_roc_auc: number;
}

// Note extraction
export interface ReviewItem {
  kind: "condition" | "medication" | "observation" | "follow_up";
  label: string;
  evidence: string | null;
  status: "new" | "already_recorded" | "dropped";
  reason: string | null;
}

export interface ConditionIn {
  icd10_code: string;
  description: string;
  status?: "active" | "resolved";
  category?: "problem" | "encounter";
  is_primary?: boolean;
}
export interface ObservationIn {
  code: string;
  value: number;
  unit?: string | null;
}
export interface MedicationIn {
  name: string;
  dose?: string | null;
  frequency?: string | null;
  route?: string | null;
  action: "started" | "continued" | "dose_increased" | "dose_decreased" | "stopped";
}

export interface EncounterDraft {
  conditions: ConditionIn[];
  observations: ObservationIn[];
  medications: MedicationIn[];
  stop_medication_ids: string[];
  follow_up_date: string | null;
}

export interface ExtractionResult {
  extractor: string;
  draft: EncounterDraft;
  review: ReviewItem[];
  warnings: string[];
}
