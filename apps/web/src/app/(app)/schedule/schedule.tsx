"use client";

import Link from "next/link";
import { useMemo } from "react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { api } from "@/lib/api";
import { titleCase } from "@/lib/format";
import { useAppointments, usePatients } from "@/lib/hooks";
import type { Appointment } from "@/lib/types";

export function Schedule() {
  return <RoleGate roles={["clinician"]}><Inner /></RoleGate>;
}

function Inner() {
  const qc = useQueryClient();
  const { data, isPending, error, refetch } = useAppointments(60);
  const patients = usePatients();
  const names = useMemo(() => Object.fromEntries((patients.data ?? []).map((p) => [p.id, p.full_name])), [patients.data]);
  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Appointment["status"] }) => api(`/appointments/${id}`, { method: "PATCH", body: { status } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["appointments"] }); toast.success("Appointment updated"); },
    onError: (e) => toast.error(e.message),
  });
  const days = useMemo(() => {
    const out = new Map<string, Appointment[]>();
    for (const a of data ?? []) {
      const d = new Date(a.starts_at).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
      out.set(d, [...(out.get(d) ?? []), a]);
    }
    return [...out.entries()];
  }, [data]);

  return (
    <>
      <PageHeader title="Schedule" description="Your appointments for the next 60 days." />
      {isPending ? <LoadingRows /> : error ? <ErrorState error={error} retry={refetch} /> : days.length === 0 ? <EmptyState title="No upcoming appointments" /> : (
        <div className="space-y-4">
          {days.map(([day, appts]) => (
            <Card key={day}>
              <CardHeader className="pb-2"><CardTitle className="text-sm">{day}</CardTitle></CardHeader>
              <CardContent className="divide-y">
                {appts.map((a) => (
                  <div key={a.id} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-4">
                      <span className="tabular w-14 text-sm font-semibold">{new Date(a.starts_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</span>
                      <div>
                        <Link href={`/patients/${a.patient_id}`} className="text-sm font-medium hover:underline">{names[a.patient_id] ?? "Patient"}</Link>
                        <p className="text-xs text-muted-foreground">{a.reason ?? "Consultation"}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {a.status !== "scheduled" ? <Badge variant="secondary">{titleCase(a.status)}</Badge> : (
                        <>
                          <Button size="sm" asChild><Link href={`/patients/${a.patient_id}/consult`}>Start visit</Link></Button>
                          <Button size="sm" variant="ghost" onClick={() => update.mutate({ id: a.id, status: "no_show" })}>No-show</Button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
