"use client";

import Link from "next/link";
import { AlertOctagon, CalendarClock, Droplets, Pill, Stethoscope } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatDateTime, OBSERVATIONS, outOfRange, relative } from "@/lib/format";
import type { PatientSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export function PatientHeader({ summary, actions }: { summary: PatientSummary; actions?: React.ReactNode }) {
  const p = summary.patient;
  const severe = summary.allergies.filter((a) => a.severity === "severe");
  return (
    <div className="mb-6 space-y-3">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">{p.full_name}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span>{p.age} y · {p.sex}</span>
            <span className="font-mono text-xs">{p.mrn}</span>
            {p.blood_group && <span className="inline-flex items-center gap-1"><Droplets className="size-3.5" aria-hidden />{p.blood_group}</span>}
            <span>{summary.encounter_count} encounters · last {relative(summary.last_encounter?.started_at)}</span>
          </p>
        </div>
        {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
      </div>
      {summary.allergies.length > 0 && (
        <div
          role={severe.length ? "alert" : undefined}
          className={cn("flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2 text-sm",
            severe.length ? "border-risk-high/40 bg-risk-high-soft text-risk-high" : "bg-muted/50")}
        >
          <AlertOctagon className="size-4" aria-hidden />
          <span className="font-medium">Allergies:</span>
          {summary.allergies.map((a) => (
            <span key={a.id} className="font-medium">
              {a.substance}
              <span className="font-normal opacity-80"> ({a.severity}{a.reaction ? `, ${a.reaction}` : ""})</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function LatestVitals({ summary }: { summary: PatientSummary }) {
  const order = Object.keys(OBSERVATIONS);
  const obs = [...summary.latest_observations].sort((a, b) => order.indexOf(a.code) - order.indexOf(b.code));
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-base">Latest measurements</CardTitle></CardHeader>
      <CardContent>
        {obs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No measurements recorded.</p>
        ) : (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
            {obs.map((o) => {
              const flag = outOfRange(o.code, o.value);
              return (
                <div key={o.code} className="min-w-0">
                  <dt className="truncate text-xs text-muted-foreground">{OBSERVATIONS[o.code]?.label ?? o.label}</dt>
                  <dd className="tabular flex items-baseline gap-1">
                    <span className={cn("text-base font-semibold", flag && "text-risk-high")}>{o.value}</span>
                    <span className="text-xs text-muted-foreground">{o.unit}</span>
                    {flag && <span className="sr-only">({flag})</span>}
                  </dd>
                  <dd className="text-[11px] text-muted-foreground">{formatDate(o.observed_at)}</dd>
                </div>
              );
            })}
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

export function ProblemsAndMeds({ summary }: { summary: PatientSummary }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader className="flex flex-row items-center gap-2 pb-2">
          <Stethoscope className="size-4 text-muted-foreground" aria-hidden />
          <CardTitle className="text-base">Active problems</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.active_conditions.length === 0 ? (
            <p className="text-sm text-muted-foreground">None recorded.</p>
          ) : (
            <ul className="space-y-2">
              {summary.active_conditions.map((c) => (
                <li key={c.id} className="flex items-start justify-between gap-2 text-sm">
                  <span>{c.description}</span>
                  <Badge variant="secondary" className="shrink-0 font-mono text-[11px]">{c.icd10_code}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center gap-2 pb-2">
          <Pill className="size-4 text-muted-foreground" aria-hidden />
          <CardTitle className="text-base">Current medications</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.active_medications.length === 0 ? (
            <p className="text-sm text-muted-foreground">None recorded.</p>
          ) : (
            <ul className="space-y-2">
              {summary.active_medications.map((m) => (
                <li key={m.id} className="text-sm">
                  <span className="font-medium">{m.name}</span>
                  <span className="text-muted-foreground"> {[m.dose, m.frequency].filter(Boolean).join(" · ")}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function UpcomingAppointments({ summary, bookHref }: { summary: PatientSummary; bookHref?: string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-2 pb-2">
        <CalendarClock className="size-4 text-muted-foreground" aria-hidden />
        <CardTitle className="text-base">Upcoming</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {summary.upcoming_appointments.length === 0 ? (
          <p className="text-sm text-muted-foreground">No upcoming appointments.</p>
        ) : (
          summary.upcoming_appointments.map((a) => (
            <div key={a.id} className="text-sm">
              <p className="font-medium">{formatDateTime(a.starts_at)}</p>
              <p className="text-muted-foreground">{a.clinician.full_name}{a.reason ? ` · ${a.reason}` : ""}</p>
            </div>
          ))
        )}
        {bookHref && <Button asChild variant="outline" size="sm" className="mt-1"><Link href={bookHref}>Book appointment</Link></Button>}
      </CardContent>
    </Card>
  );
}
