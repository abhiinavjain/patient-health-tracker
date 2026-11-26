"use client";

import { useState } from "react";
import { AlertTriangle, BellRing, Check, Phone, Siren } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { keys, usePatientAlerts } from "@/lib/hooks";
import type { AlertItem, AlertLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

export const LEVEL_TEXT: Record<AlertLevel, string> = { critical: "Critical", urgent: "Urgent", watch: "Watch" };
export const LEVEL_CLASS: Record<AlertLevel, string> = {
  critical: "border-risk-high/50 bg-risk-high-soft text-risk-high",
  urgent: "border-risk-moderate/50 bg-risk-moderate-soft text-risk-moderate",
  watch: "border-border bg-muted/60 text-foreground",
};

export function AlertBadge({ level }: { level: AlertLevel }) {
  return <Badge variant="outline" className={cn("font-semibold", LEVEL_CLASS[level])}>{LEVEL_TEXT[level]}</Badge>;
}

function Reasons({ alert }: { alert: AlertItem }) {
  return (
    <ul className="mt-2 space-y-1 text-sm">
      {alert.reasons.map((r, i) => (
        <li key={i} className="flex flex-wrap gap-x-2">
          <span className="font-semibold tabular">{r.label} {r.value} {r.unit}</span>
          <span className="opacity-80">— {r.rule}</span>
        </li>
      ))}
    </ul>
  );
}

function ReviewDialog({ alert, patientId }: { alert: AlertItem; patientId: string }) {
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);
  const review = useMutation({
    mutationFn: (release: boolean) =>
      api(`/patients/${patientId}/alerts/${alert.id}/review`, { method: "POST", body: { release_to_patient: release, note: note || null } }),
    onSuccess: (_, release) => {
      qc.invalidateQueries({ queryKey: keys.patient(patientId) });
      qc.invalidateQueries({ queryKey: ["open-alerts"] });
      setOpen(false);
      toast.success(release ? "Reviewed — the patient will see this alert and the advice" : "Alert marked as reviewed");
    },
    onError: (e) => toast.error(e.message),
  });
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant={alert.level === "critical" ? "destructive" : "default"}>Review</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Review {LEVEL_TEXT[alert.level].toLowerCase()} alert</DialogTitle>
          <DialogDescription>
            Notifying the patient shows them this alert with advice to{" "}
            {alert.level === "critical" ? "go to the nearest emergency department or call 108" : alert.level === "urgent" ? "contact their doctor today" : "keep monitoring"}.
          </DialogDescription>
        </DialogHeader>
        <Reasons alert={alert} />
        <Textarea placeholder="Note for the record (and the patient, if notified) — e.g. 'Called patient, advised ER visit'"
                  value={note} onChange={(e) => setNote(e.target.value)} rows={3} aria-label="Review note" />
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => review.mutate(false)} disabled={review.isPending}><Check aria-hidden /> Mark reviewed</Button>
          <Button onClick={() => review.mutate(true)} disabled={review.isPending}><BellRing aria-hidden /> Review &amp; notify patient</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Unreviewed alerts on a patient's chart (clinician view). */
export function ClinicianAlerts({ patientId }: { patientId: string }) {
  const { data } = usePatientAlerts(patientId, true);
  if (!data?.length) return null;
  return (
    <div className="mb-6 space-y-3">
      {data.map((a) => (
        <div key={a.id} role={a.level === "critical" ? "alert" : "status"} className={cn("rounded-lg border p-4", LEVEL_CLASS[a.level])}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="flex items-center gap-2 font-semibold">
                {a.level === "critical" ? <Siren className="size-4" aria-hidden /> : <AlertTriangle className="size-4" aria-hidden />}
                {LEVEL_TEXT[a.level]}: {a.level === "critical" ? "needs immediate action" : a.level === "urgent" ? "needs review today" : "keep an eye on this"}
              </p>
              <p className="text-xs opacity-80">
                {formatDateTime(a.created_at)} · {a.source === "patient" ? "patient-entered reading" : "recorded at a visit"}
                {a.news2 != null && ` · NEWS2 ${a.news2} (partial)`}
              </p>
              <Reasons alert={a} />
            </div>
            <ReviewDialog alert={a} patientId={patientId} />
          </div>
        </div>
      ))}
    </div>
  );
}

const PATIENT_ADVICE: Record<AlertLevel, { title: string; text: string }> = {
  critical: {
    title: "Your recent readings need urgent medical attention",
    text: "Go to the nearest emergency department or call 108 now. Don't drive yourself if you feel unwell.",
  },
  urgent: { title: "Please contact your doctor today", text: "Your doctor reviewed your recent readings and wants you seen soon." },
  watch: { title: "Your doctor reviewed your readings", text: "Keep monitoring and follow your care plan. Seek help if you feel worse." },
};

/** Alerts a clinician has released to the patient (patient view). */
export function PatientAlerts({ patientId }: { patientId: string }) {
  const qc = useQueryClient();
  const { data } = usePatientAlerts(patientId);
  const seen = useMutation({
    mutationFn: (id: string) => api(`/patients/${patientId}/alerts/${id}/seen`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.patient(patientId) }),
  });
  const [cutoff] = useState(() => Date.now() - 7 * 86_400_000); // show alerts reviewed in the last 7 days
  const recent = (data ?? []).filter((a) => new Date(a.reviewed_at ?? a.created_at).getTime() >= cutoff);
  if (!recent.length) return null;
  return (
    <div className="mb-6 space-y-3">
      {recent.map((a) => {
        const advice = PATIENT_ADVICE[a.level];
        return (
          <div key={a.id} role="alert" className={cn("rounded-lg border p-4", LEVEL_CLASS[a.level], a.level === "critical" && "border-2")}>
            <p className="flex items-center gap-2 text-base font-semibold">
              {a.level === "critical" ? <Siren className="size-5" aria-hidden /> : <AlertTriangle className="size-5" aria-hidden />}
              {advice.title}
            </p>
            <p className="mt-1 text-sm">{advice.text}</p>
            {a.review_note && <p className="mt-2 text-sm"><span className="font-medium">{a.reviewer_name ?? "Your doctor"}:</span> {a.review_note}</p>}
            <Reasons alert={a} />
            <div className="mt-3 flex flex-wrap gap-2">
              {a.level === "critical" && (
                <Button asChild variant="destructive" size="sm"><a href="tel:108"><Phone aria-hidden /> Call 108</a></Button>
              )}
              {!a.patient_seen_at && (
                <Button size="sm" variant="outline" className="bg-background" onClick={() => seen.mutate(a.id)}>I’ve seen this</Button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
