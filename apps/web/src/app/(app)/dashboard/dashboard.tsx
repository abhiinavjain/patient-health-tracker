"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { AlertTriangle, CalendarClock, ChevronRight, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { RiskBadge } from "@/components/risk/risk-card";
import { formatDateTime, MODEL_SHORT, pct, relative } from "@/lib/format";
import { useAppointments, useMe, useOpenAlerts, usePatients, useWorklist } from "@/lib/hooks";
import { AlertBadge } from "@/components/alerts/alerts";

function Stat({ icon: Icon, label, value, hint }: { icon: typeof Users; label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card className="gap-2 py-4">
      <CardContent className="flex items-center gap-3 px-4">
        <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary"><Icon className="size-5" aria-hidden /></span>
        <div>
          <p className="tabular text-2xl font-semibold leading-none">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{label}{hint ? ` · ${hint}` : ""}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// "Dr. Ritu Malhotra" -> "Dr. Malhotra"; other names -> first name.
function greetingName(name: string) {
  const parts = name.split(/\s+/).filter(Boolean);
  return /^dr\.?$/i.test(parts[0] ?? "") ? `Dr. ${parts.at(-1)}` : (parts[0] ?? "");
}

export function Dashboard() {
  return <RoleGate roles={["clinician"]}><Inner /></RoleGate>;
}

function Inner() {
  const router = useRouter();
  const { data: me } = useMe();
  const worklist = useWorklist();
  const alerts = useOpenAlerts();
  const patients = usePatients();
  const appts = useAppointments(7);
  const highCount = useMemo(() => new Set((worklist.data ?? []).filter((w) => w.band === "high").map((w) => w.patient_id)).size, [worklist.data]);
  const today = (appts.data ?? []).filter((a) => new Date(a.starts_at).toDateString() === new Date().toDateString());
  const hour = new Date().getHours();

  return (
    <>
      <PageHeader
        title={`Good ${hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening"}, ${greetingName(me?.full_name ?? "")}`}
        description="Patients on your panel who may need attention, ranked by risk."
        actions={<Button asChild><Link href="/patients">Find a patient</Link></Button>}
      />
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <Stat icon={Users} label="Patients on your panel" value={patients.data?.length ?? "—"} />
        <Stat icon={AlertTriangle} label="High-risk patients" value={worklist.isPending ? "—" : highCount} hint="any model" />
        <Stat icon={CalendarClock} label="Appointments today" value={appts.isPending ? "—" : today.length} hint={`${appts.data?.length ?? 0} this week`} />
      </div>

      {(alerts.data ?? []).length > 0 && (
        <Card className="mb-4 border-risk-high/40">
          <CardHeader>
            <CardTitle className="text-base">Needs attention now</CardTitle>
            <CardDescription>New readings that crossed clinical thresholds (NEWS2, critical values). Review each one.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            {alerts.data!.slice(0, 10).map((a) => (
              <Link key={a.id} href={`/patients/${a.patient_id}`} className="-mx-2 flex items-center gap-3 rounded-md px-2 py-2 hover:bg-accent">
                <AlertBadge level={a.level} />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium">{a.patient_name}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {a.reasons.map((r) => `${r.label} ${r.value}`).join(" · ")}{a.source === "patient" ? " · home reading" : ""}
                  </span>
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">{relative(a.created_at)}</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_22rem]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk worklist</CardTitle>
            <CardDescription>Latest moderate and high scores. Ranked by band, then by how a patient compares to the reference population.</CardDescription>
          </CardHeader>
          <CardContent className="px-0">
            {worklist.isPending ? <div className="px-6"><LoadingRows /></div> : worklist.error ? <div className="px-6"><ErrorState error={worklist.error} retry={worklist.refetch} /></div> :
              worklist.data.length === 0 ? <div className="px-6"><EmptyState title="No elevated risks on your panel" /></div> : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-6">Patient</TableHead><TableHead>Model</TableHead><TableHead>Risk</TableHead>
                    <TableHead className="hidden lg:table-cell">Main driver</TableHead><TableHead className="pr-6 text-right">Scored</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {worklist.data.slice(0, 25).map((w) => (
                    <TableRow key={`${w.patient_id}-${w.model}`} className="cursor-pointer" onClick={() => router.push(`/patients/${w.patient_id}`)}>
                      <TableCell className="pl-6 font-medium">
                        <Link href={`/patients/${w.patient_id}`} className="hover:underline" onClick={(e) => e.stopPropagation()}>{w.patient_name}</Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{MODEL_SHORT[w.model] ?? w.model}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <RiskBadge band={w.band} />
                          <span className="tabular text-xs text-muted-foreground">{pct(w.score)} · p{w.percentile}</span>
                        </div>
                      </TableCell>
                      <TableCell className="hidden max-w-xs truncate text-sm text-muted-foreground lg:table-cell">{w.top_factor}</TableCell>
                      <TableCell className="pr-6 text-right text-xs text-muted-foreground">{relative(w.computed_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">This week</CardTitle>
            <CardDescription>Your upcoming appointments</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            {appts.isPending ? <LoadingRows rows={3} /> : (appts.data ?? []).length === 0 ? <EmptyState title="No appointments this week" /> :
              (appts.data ?? []).slice(0, 8).map((a) => (
                <Link key={a.id} href={`/patients/${a.patient_id}`} className="-mx-2 flex items-center justify-between rounded-md px-2 py-2 hover:bg-accent">
                  <span>
                    <span className="block text-sm font-medium">{formatDateTime(a.starts_at)}</span>
                    <span className="block text-xs text-muted-foreground">{a.reason ?? "Consultation"}</span>
                  </span>
                  <ChevronRight className="size-4 text-muted-foreground" aria-hidden />
                </Link>
              ))}
            <Button asChild variant="outline" size="sm" className="mt-2 w-full"><Link href="/schedule">Full schedule</Link></Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
