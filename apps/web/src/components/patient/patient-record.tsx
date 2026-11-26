"use client";

import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ErrorState } from "@/components/states";
import { RiskCard } from "@/components/risk/risk-card";
import { LatestVitals, PatientHeader, ProblemsAndMeds, UpcomingAppointments } from "./summary";
import { Timeline } from "./timeline";
import { TrendChart } from "./trend-chart";
import { formatDate, titleCase } from "@/lib/format";
import { useConditions, useMedications, useRisk, useSummary } from "@/lib/hooks";

function RiskGrid({ patientId, audience }: { patientId: string; audience: "clinician" | "patient" }) {
  const { data, isPending, error, refetch } = useRisk(patientId);
  if (isPending) return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-64" />)}</div>;
  if (error) return <ErrorState error={error} retry={refetch} />;
  // Scored results first, so the actionable ones are seen.
  const sorted = [...data].sort((a, b) => Number(b.status === "scored") - Number(a.status === "scored"));
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {sorted.map((r) => <RiskCard key={r.model} risk={r} audience={audience} />)}
    </div>
  );
}

function History({ patientId }: { patientId: string }) {
  const meds = useMedications(patientId);
  const conds = useConditions(patientId);
  const problems = (conds.data ?? []).filter((c) => c.category === "problem");
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Medication history</CardTitle></CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader><TableRow><TableHead className="pl-6">Medication</TableHead><TableHead>Dose</TableHead><TableHead>Since</TableHead><TableHead className="pr-6">Status</TableHead></TableRow></TableHeader>
            <TableBody>
              {(meds.data ?? []).filter((m) => m.action !== "stopped").map((m) => (
                <TableRow key={m.id}>
                  <TableCell className="pl-6 font-medium">{m.name}</TableCell>
                  <TableCell className="text-muted-foreground">{[m.dose, m.frequency].filter(Boolean).join(" · ") || "—"}</TableCell>
                  <TableCell className="tabular text-muted-foreground">{formatDate(m.start_date)}</TableCell>
                  <TableCell className="pr-6">
                    <Badge variant={m.status === "active" ? "default" : "secondary"}>{m.status === "active" ? "Active" : `Stopped ${formatDate(m.end_date)}`}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Problem list</CardTitle></CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader><TableRow><TableHead className="pl-6">Condition</TableHead><TableHead>ICD-10</TableHead><TableHead>Onset</TableHead><TableHead className="pr-6">Status</TableHead></TableRow></TableHeader>
            <TableBody>
              {problems.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="pl-6 font-medium">{c.description}</TableCell>
                  <TableCell className="font-mono text-xs">{c.icd10_code}</TableCell>
                  <TableCell className="tabular text-muted-foreground">{formatDate(c.onset_date)}</TableCell>
                  <TableCell className="pr-6"><Badge variant={c.status === "active" ? "default" : "secondary"}>{titleCase(c.status)}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

export function PatientRecord({
  patientId, audience, actions, bookHref,
}: { patientId: string; audience: "clinician" | "patient"; actions?: ReactNode; bookHref?: string }) {
  const { data: summary, isPending, error, refetch } = useSummary(patientId);
  if (isPending) return <div className="space-y-4"><Skeleton className="h-16" /><Skeleton className="h-10 w-80" /><Skeleton className="h-72" /></div>;
  if (error) return <ErrorState error={error} retry={refetch} />;
  return (
    <>
      <PatientHeader summary={summary} actions={actions} />
      <Tabs defaultValue="overview" className="gap-6">
        <TabsList className="h-auto max-w-full flex-wrap justify-start">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="risk">Risk</TabsTrigger>
          <TabsTrigger value="timeline">History</TabsTrigger>
          <TabsTrigger value="meds">Medications &amp; problems</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[1fr_20rem]">
            <div className="space-y-4">
              <ProblemsAndMeds summary={summary} />
              <TrendChart patientId={patientId} compact />
            </div>
            <div className="space-y-4">
              <LatestVitals summary={summary} />
              <UpcomingAppointments summary={summary} bookHref={bookHref} />
            </div>
          </div>
        </TabsContent>
        <TabsContent value="risk" className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {audience === "patient"
              ? "These estimates come from models trained on large public health datasets. They are a prompt for a conversation with your doctor, not a diagnosis."
              : "Calibrated model estimates with the factors that drive them (TreeSHAP). Decision support only."}
          </p>
          <RiskGrid patientId={patientId} audience={audience} />
          <TrendChart patientId={patientId} />
        </TabsContent>
        <TabsContent value="timeline"><Timeline patientId={patientId} /></TabsContent>
        <TabsContent value="meds"><History patientId={patientId} /></TabsContent>
      </Tabs>
    </>
  );
}
