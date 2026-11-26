"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type {
  Allergy, Appointment, AuditEntry, Clinician, Condition, Encounter, EncounterSummary, Grant, Lifestyle, Medication,
  ModelMonitor, ObservationSeries, Overview, Patient, PatientListItem, PatientSummary, RiskModelInfo, RiskResult,
  TimelineEvent, User, WorklistRow,
} from "./types";

export const keys = {
  me: ["me"] as const,
  patients: (q: string) => ["patients", q] as const,
  patient: (id: string) => ["patient", id] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: () => api<User>("/auth/me"), staleTime: 60_000 });

export const usePatients = (q = "") =>
  useQuery({ queryKey: keys.patients(q), queryFn: () => api<PatientListItem[]>(`/patients?limit=200${q ? `&q=${encodeURIComponent(q)}` : ""}`) });

export const usePatient = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "info"], queryFn: () => api<Patient>(`/patients/${id}`), enabled: !!id });

export const useSummary = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "summary"], queryFn: () => api<PatientSummary>(`/patients/${id}/summary`), enabled: !!id });

export const useTimeline = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "timeline"], queryFn: () => api<TimelineEvent[]>(`/patients/${id}/timeline?limit=300`), enabled: !!id });

export const useSeries = (id: string, codes: string[]) =>
  useQuery({
    queryKey: [...keys.patient(id), "series", codes.join(",")],
    queryFn: () => api<ObservationSeries[]>(`/patients/${id}/observations/series?codes=${codes.join(",")}`),
    enabled: !!id && codes.length > 0,
  });

export const useRisk = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "risk"], queryFn: () => api<RiskResult[]>(`/patients/${id}/risk`), enabled: !!id });

export const useEncounters = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "encounters"], queryFn: () => api<EncounterSummary[]>(`/patients/${id}/encounters`), enabled: !!id });

export const useEncounter = (id: string, eid: string | null) =>
  useQuery({ queryKey: [...keys.patient(id), "encounter", eid], queryFn: () => api<Encounter>(`/patients/${id}/encounters/${eid}`), enabled: !!id && !!eid });

export const useConditions = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "conditions"], queryFn: () => api<Condition[]>(`/patients/${id}/conditions`), enabled: !!id });

export const useMedications = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "medications"], queryFn: () => api<Medication[]>(`/patients/${id}/medications`), enabled: !!id });

export const useAllergies = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "allergies"], queryFn: () => api<Allergy[]>(`/patients/${id}/allergies`), enabled: !!id });

export const useLifestyle = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "lifestyle"], queryFn: () => api<Lifestyle[]>(`/patients/${id}/lifestyle`), enabled: !!id });

export const useGrants = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "grants"], queryFn: () => api<Grant[]>(`/patients/${id}/access`), enabled: !!id });

export const usePatientAudit = (id: string) =>
  useQuery({ queryKey: [...keys.patient(id), "audit"], queryFn: () => api<AuditEntry[]>(`/patients/${id}/audit?limit=200`), enabled: !!id });

export const useClinicians = () => useQuery({ queryKey: ["clinicians"], queryFn: () => api<Clinician[]>("/clinicians"), staleTime: 300_000 });

export const useAppointments = (daysAhead = 30) =>
  useQuery({ queryKey: ["appointments", daysAhead], queryFn: () => api<Appointment[]>(`/appointments?days_ahead=${daysAhead}`) });

export const useWorklist = () => useQuery({ queryKey: ["worklist"], queryFn: () => api<WorklistRow[]>("/analytics/worklist") });

export const useOverview = (months = 12) =>
  useQuery({ queryKey: ["overview", months], queryFn: () => api<Overview>(`/analytics/overview?months=${months}`) });

export const useModelMonitoring = () => useQuery({ queryKey: ["model-monitoring"], queryFn: () => api<ModelMonitor[]>("/analytics/models") });

export const useRiskModels = () => useQuery({ queryKey: ["risk-models"], queryFn: () => api<RiskModelInfo[]>("/risk/models"), staleTime: 3_600_000 });

export const useAdminUsers = () => useQuery({ queryKey: ["admin-users"], queryFn: () => api<User[]>("/admin/users?limit=500") });

export const useAdminAudit = (action?: string) =>
  useQuery({ queryKey: ["admin-audit", action], queryFn: () => api<AuditEntry[]>(`/admin/audit?limit=300${action ? `&action=${action}` : ""}`) });
