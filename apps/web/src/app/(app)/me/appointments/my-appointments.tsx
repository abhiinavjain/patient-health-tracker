"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyState, LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { api } from "@/lib/api";
import { formatDateTime, titleCase } from "@/lib/format";
import { useAppointments, useClinicians, useGrants, useMe } from "@/lib/hooks";

export function MyAppointments() {
  return <RoleGate roles={["patient"]}><Inner /></RoleGate>;
}

function Inner() {
  const { data: me } = useMe();
  const pid = me?.patient_id ?? "";
  const qc = useQueryClient();
  const appts = useAppointments(365);
  const clinicians = useClinicians();
  const grants = useGrants(pid);
  const [form, setForm] = useState({ clinician_id: "", starts_at: "", reason: "" });
  const [minWhen] = useState(() => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16));
  const needsGrant = form.clinician_id && !(grants.data ?? []).some((g) => g.clinician.id === form.clinician_id);

  const book = useMutation({
    mutationFn: () => api(`/patients/${pid}/appointments`, { method: "POST", body: { ...form, starts_at: new Date(form.starts_at).toISOString(), reason: form.reason || null } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["appointments"] });
      qc.invalidateQueries({ queryKey: ["patient", pid] });
      setForm({ clinician_id: "", starts_at: "", reason: "" });
      toast.success("Appointment booked");
    },
    onError: (e) => toast.error(e.message),
  });
  const cancel = useMutation({
    mutationFn: (id: string) => api(`/appointments/${id}`, { method: "PATCH", body: { status: "cancelled" } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["appointments"] }); toast.success("Appointment cancelled"); },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader title="Appointments" />
      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <Card>
          <CardHeader><CardTitle className="text-base">Upcoming</CardTitle></CardHeader>
          <CardContent className="divide-y">
            {appts.isPending ? <LoadingRows rows={3} /> : (appts.data ?? []).length === 0 ? <EmptyState title="No upcoming appointments" /> :
              appts.data!.map((a) => (
                <div key={a.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium">{formatDateTime(a.starts_at)}</p>
                    <p className="text-sm text-muted-foreground">{a.clinician.full_name} · {a.clinician.specialty}{a.reason ? ` · ${a.reason}` : ""}</p>
                  </div>
                  {a.status === "scheduled" ? (
                    <Button variant="ghost" size="sm" onClick={() => cancel.mutate(a.id)} disabled={cancel.isPending}>Cancel</Button>
                  ) : <Badge variant="secondary">{titleCase(a.status)}</Badge>}
                </div>
              ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Book a visit</CardTitle><CardDescription>Choose a doctor and time.</CardDescription></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); book.mutate(); }}>
              <div className="space-y-2">
                <Label htmlFor="doc">Doctor</Label>
                <Select value={form.clinician_id} onValueChange={(v) => setForm({ ...form, clinician_id: v })}>
                  <SelectTrigger id="doc" className="w-full"><SelectValue placeholder="Select a doctor" /></SelectTrigger>
                  <SelectContent>{(clinicians.data ?? []).map((c) => <SelectItem key={c.id} value={c.id}>{c.full_name} — {c.specialty}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="when">Date & time</Label>
                <Input id="when" type="datetime-local" required value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
                       min={minWhen} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="why">Reason (optional)</Label>
                <Input id="why" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
              </div>
              {needsGrant && (
                <Alert><AlertDescription className="text-xs">Booking will give this doctor access to your record. You can revoke it anytime under Privacy &amp; access.</AlertDescription></Alert>
              )}
              <Button type="submit" className="w-full" disabled={!form.clinician_id || !form.starts_at || book.isPending}>
                {book.isPending && <Loader2 className="animate-spin" aria-hidden />} Book appointment
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
