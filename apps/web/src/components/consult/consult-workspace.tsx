"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowLeft, Check, CircleSlash, Loader2, Plus, Sparkles, Trash2, Undo2 } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState } from "@/components/states";
import { api } from "@/lib/api";
import { OBSERVATIONS, titleCase } from "@/lib/format";
import { keys, useSummary } from "@/lib/hooks";
import type { ConditionIn, Encounter, ExtractionResult, MedicationIn, ObservationIn, ReviewItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const ACTIONS: MedicationIn["action"][] = ["started", "continued", "dose_increased", "dose_decreased"];
const FREQUENCIES = ["once daily", "twice daily", "three times daily", "four times daily", "at night", "as needed", "weekly", "with meals"];
const SAMPLE = `Follow-up. Known HTN, T2DM. Feels well, no chest pain. Occasional tingling in feet.
BP 152/94, HR 80, Wt 84 kg. HbA1c 8.6%, LDL 132.
Telmisartan increased to 80 mg OD. Start empagliflozin 10 mg OD. Start atorvastatin 20 mg at night.
Review in 6 weeks with HbA1c.`;

const localNow = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
};

function ReviewList({ items }: { items: ReviewItem[] }) {
  const groups: [ReviewItem["status"], string][] = [["new", "Added to draft"], ["already_recorded", "Already on the chart"], ["dropped", "Dropped by validation"]];
  return (
    <div className="space-y-4">
      {groups.map(([status, title]) => {
        const list = items.filter((i) => i.status === status);
        if (!list.length) return null;
        return (
          <div key={status}>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {status === "new" ? <Check className="size-3.5" aria-hidden /> : status === "dropped" ? <CircleSlash className="size-3.5" aria-hidden /> : <Undo2 className="size-3.5" aria-hidden />}
              {title} ({list.length})
            </p>
            <ul className="space-y-1.5">
              {list.map((i, n) => (
                <li key={n} className={cn("rounded-md border px-3 py-2 text-sm", status === "dropped" && "border-dashed opacity-75")}>
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-medium">{i.label}</span>
                    <Badge variant="outline" className="shrink-0 text-[10px] uppercase">{i.kind.replace("_", "-")}</Badge>
                  </div>
                  {i.evidence && <p className="mt-1 truncate text-xs text-muted-foreground" title={i.evidence}>“{i.evidence}”</p>}
                  {i.reason && <p className="mt-0.5 text-xs text-muted-foreground">{i.reason}</p>}
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

export function ConsultWorkspace({ patientId }: { patientId: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const summary = useSummary(patientId);

  const [type, setType] = useState("outpatient");
  const [startedAt, setStartedAt] = useState(localNow);
  const [endedAt, setEndedAt] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [admission, setAdmission] = useState({ admission_type: "", admission_source: "", discharge_disposition: "" });
  const [conditions, setConditions] = useState<ConditionIn[]>([]);
  const [observations, setObservations] = useState<ObservationIn[]>([]);
  const [medications, setMedications] = useState<MedicationIn[]>([]);
  const [stopIds, setStopIds] = useState<string[]>([]);
  const [followUp, setFollowUp] = useState("");
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);

  const extract = useMutation({
    mutationFn: () => api<ExtractionResult>(`/patients/${patientId}/notes/extract`, {
      method: "POST", body: { note, visit_at: new Date(startedAt).toISOString() },
    }),
    onSuccess: (r) => {
      setExtraction(r);
      // Merge into the draft without duplicating anything the clinician already added.
      setConditions((c) => [...c, ...r.draft.conditions.filter((d) => !c.some((x) => x.icd10_code === d.icd10_code))]);
      setObservations((o) => [...o, ...r.draft.observations.filter((d) => !o.some((x) => x.code === d.code))]);
      setMedications((m) => [...m, ...r.draft.medications.filter((d) => !m.some((x) => x.name.toLowerCase() === d.name.toLowerCase()))]);
      setStopIds((s) => [...new Set([...s, ...r.draft.stop_medication_ids])]);
      if (r.draft.follow_up_date) setFollowUp(r.draft.follow_up_date);
      const added = r.review.filter((i) => i.status === "new").length;
      const known = r.review.filter((i) => i.status === "already_recorded").length;
      if (added) toast.success(`${added} item${added > 1 ? "s" : ""} added to the draft — please review`);
      else if (known) toast.info("Everything recognised in the note is already on the chart");
      else toast.warning("No diagnoses, medications or measurements recognised — add them to the draft manually");
    },
    onError: (e) => toast.error(e.message),
  });

  const save = useMutation({
    mutationFn: () => api<Encounter>(`/patients/${patientId}/encounters`, {
      method: "POST",
      body: {
        type,
        started_at: new Date(startedAt).toISOString(),
        ended_at: endedAt ? new Date(endedAt).toISOString() : type === "inpatient" ? null : new Date(startedAt).toISOString(),
        reason: reason || null,
        notes: note || null,
        ...(type === "inpatient" ? Object.fromEntries(Object.entries(admission).map(([k, v]) => [k, v || null])) : {}),
        conditions: conditions.filter((c) => c.icd10_code && c.description),
        observations: observations.filter((o) => o.code && Number.isFinite(o.value)),
        medications: medications.filter((m) => m.name),
        stop_medication_ids: stopIds,
        follow_up_date: followUp || null,
      },
    }),
    onSuccess: (enc) => {
      qc.invalidateQueries({ queryKey: keys.patient(patientId) });
      qc.invalidateQueries({ queryKey: ["worklist"] });
      qc.invalidateQueries({ queryKey: ["patients"] });
      qc.invalidateQueries({ queryKey: ["open-alerts"] });
      const a = enc.alert;
      if (a?.level === "critical")
        toast.error(`Critical: ${a.reasons[0]?.rule ?? "readings need immediate action"}. Review the alert on the chart.`, { duration: 12000 });
      else if (a?.level === "urgent")
        toast.warning(`Urgent: ${a.reasons[0]?.rule ?? "readings need review today"}. Review the alert on the chart.`, { duration: 10000 });
      else toast.success(a ? "Consultation saved — minor deviations flagged for review" : "Consultation saved — readings within safe limits");
      router.push(`/patients/${patientId}`);
    },
    onError: (e) => toast.error(e.message),
  });

  const activeMeds = summary.data?.active_medications ?? [];
  const itemCount = conditions.length + observations.length + medications.length + stopIds.length;
  const obsCodes = useMemo(() => Object.entries(OBSERVATIONS), []);

  if (summary.isPending) return <Skeleton className="h-96" />;
  if (summary.error) return <ErrorState error={summary.error} />;
  const p = summary.data.patient;

  return (
    <div className="space-y-6">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2 text-muted-foreground">
          <Link href={`/patients/${patientId}`}><ArrowLeft aria-hidden /> {p.full_name}</Link>
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight">New consultation</h1>
        <p className="text-sm text-muted-foreground">{p.full_name} · {p.age} y · {p.sex} · {p.mrn}</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* ---------------------------------------------------------------- note + extraction */}
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Visit</CardTitle></CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="type">Type</Label>
                <Select value={type} onValueChange={setType}>
                  <SelectTrigger id="type" className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>{["outpatient", "inpatient", "emergency", "telehealth"].map((t) => <SelectItem key={t} value={t}>{titleCase(t)}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="start">{type === "inpatient" ? "Admitted" : "Date & time"}</Label>
                <Input id="start" type="datetime-local" value={startedAt} onChange={(e) => setStartedAt(e.target.value)} />
              </div>
              {type === "inpatient" && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="end">Discharged</Label>
                    <Input id="end" type="datetime-local" value={endedAt} onChange={(e) => setEndedAt(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="disp">Discharged to</Label>
                    <Select value={admission.discharge_disposition} onValueChange={(v) => setAdmission({ ...admission, discharge_disposition: v })}>
                      <SelectTrigger id="disp" className="w-full"><SelectValue placeholder="Select" /></SelectTrigger>
                      <SelectContent>{["home", "home_health", "facility", "left_ama", "other"].map((t) => <SelectItem key={t} value={t}>{titleCase(t)}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="atype">Admission type</Label>
                    <Select value={admission.admission_type} onValueChange={(v) => setAdmission({ ...admission, admission_type: v })}>
                      <SelectTrigger id="atype" className="w-full"><SelectValue placeholder="Select" /></SelectTrigger>
                      <SelectContent>{["emergency", "urgent", "elective"].map((t) => <SelectItem key={t} value={t}>{titleCase(t)}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="asrc">Admitted from</Label>
                    <Select value={admission.admission_source} onValueChange={(v) => setAdmission({ ...admission, admission_source: v })}>
                      <SelectTrigger id="asrc" className="w-full"><SelectValue placeholder="Select" /></SelectTrigger>
                      <SelectContent>{["emergency_room", "referral", "transfer", "other"].map((t) => <SelectItem key={t} value={t}>{titleCase(t)}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                </>
              )}
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="reason">Reason for visit</Label>
                <Input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Diabetes follow-up" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Clinical note</CardTitle>
              <CardDescription>Write as you normally would. Abbreviations, brand names and Hinglish are fine.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={9} className="font-mono text-sm"
                        placeholder="Known HTN, T2DM. BP 150/90. Start metformin 500 mg BD. Review in 4 weeks." aria-label="Clinical note" />
              <div className="flex flex-wrap items-center gap-2">
                <Button onClick={() => extract.mutate()} disabled={note.trim().length < 10 || extract.isPending}>
                  {extract.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <Sparkles aria-hidden />} Extract to draft
                </Button>
                {!note && <Button variant="ghost" size="sm" onClick={() => setNote(SAMPLE)}>Insert sample note</Button>}
                <span className="text-xs text-muted-foreground">Runs on this server, so the note never leaves it.</span>
              </div>
              {extraction?.warnings.map((w) => (
                <Alert key={w}><AlertDescription className="text-sm">{w}</AlertDescription></Alert>
              ))}
              {extraction && extraction.review.length === 0 && (
                <Alert>
                  <AlertDescription className="text-sm">
                    Nothing in this note matched a diagnosis, medication, measurement or follow-up the extractor knows.
                    Symptoms, ordered tests and referrals aren’t extracted. Use “Add” in the draft for anything that should be
                    recorded; the note itself is saved with the visit.
                  </AlertDescription>
                </Alert>
              )}
              {extraction && <ReviewList items={extraction.review} />}
            </CardContent>
          </Card>
        </div>

        {/* ---------------------------------------------------------------- editable draft */}
        <div className="space-y-4 xl:sticky xl:top-20 xl:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Draft record update</CardTitle>
              <CardDescription>Check every item. Nothing is saved until you press Save.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <section aria-labelledby="dx">
                <div className="mb-2 flex items-center justify-between">
                  <h3 id="dx" className="text-sm font-medium">Diagnoses</h3>
                  <Button variant="ghost" size="sm" onClick={() => setConditions([...conditions, { icd10_code: "", description: "" }])}><Plus aria-hidden /> Add</Button>
                </div>
                {conditions.length === 0 && <p className="text-xs text-muted-foreground">None.</p>}
                <div className="space-y-2">
                  {conditions.map((c, i) => (
                    <div key={i} className="grid grid-cols-[6.5rem_1fr_auto] gap-2">
                      <Input aria-label="ICD-10 code" placeholder="ICD-10" value={c.icd10_code} className="font-mono"
                             onChange={(e) => setConditions(conditions.map((x, j) => j === i ? { ...x, icd10_code: e.target.value.toUpperCase() } : x))} />
                      <Input aria-label="Diagnosis" placeholder="Description" value={c.description}
                             onChange={(e) => setConditions(conditions.map((x, j) => j === i ? { ...x, description: e.target.value } : x))} />
                      <Button variant="ghost" size="icon" aria-label="Remove diagnosis" onClick={() => setConditions(conditions.filter((_, j) => j !== i))}><Trash2 /></Button>
                    </div>
                  ))}
                </div>
              </section>

              <section aria-labelledby="obs">
                <div className="mb-2 flex items-center justify-between">
                  <h3 id="obs" className="text-sm font-medium">Measurements</h3>
                  <Button variant="ghost" size="sm" onClick={() => setObservations([...observations, { code: "bp_systolic", value: NaN }])}><Plus aria-hidden /> Add</Button>
                </div>
                {observations.length === 0 && <p className="text-xs text-muted-foreground">None.</p>}
                <div className="space-y-2">
                  {observations.map((o, i) => (
                    <div key={i} className="grid grid-cols-[1fr_7rem_auto] gap-2">
                      <Select value={o.code} onValueChange={(v) => setObservations(observations.map((x, j) => j === i ? { ...x, code: v, unit: null } : x))}>
                        <SelectTrigger aria-label="Measurement" className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>{obsCodes.map(([code, m]) => <SelectItem key={code} value={code}>{m.label} ({m.unit})</SelectItem>)}</SelectContent>
                      </Select>
                      <Input aria-label="Value" type="number" step="any" value={Number.isFinite(o.value) ? o.value : ""}
                             onChange={(e) => setObservations(observations.map((x, j) => j === i ? { ...x, value: e.target.valueAsNumber } : x))} />
                      <Button variant="ghost" size="icon" aria-label="Remove measurement" onClick={() => setObservations(observations.filter((_, j) => j !== i))}><Trash2 /></Button>
                    </div>
                  ))}
                </div>
              </section>

              <section aria-labelledby="meds">
                <div className="mb-2 flex items-center justify-between">
                  <h3 id="meds" className="text-sm font-medium">Medication changes</h3>
                  <Button variant="ghost" size="sm" onClick={() => setMedications([...medications, { name: "", action: "started" }])}><Plus aria-hidden /> Add</Button>
                </div>
                {medications.length === 0 && <p className="text-xs text-muted-foreground">None.</p>}
                <div className="space-y-3">
                  {medications.map((m, i) => (
                    <div key={i} className="grid grid-cols-2 gap-2 rounded-md border p-2 sm:grid-cols-[1fr_6rem_9rem_9rem_auto]">
                      <Input aria-label="Medication" placeholder="Generic name" value={m.name} className="col-span-2 sm:col-span-1"
                             onChange={(e) => setMedications(medications.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
                      <Input aria-label="Dose" placeholder="Dose" value={m.dose ?? ""}
                             onChange={(e) => setMedications(medications.map((x, j) => j === i ? { ...x, dose: e.target.value } : x))} />
                      <Select value={m.frequency ?? ""} onValueChange={(v) => setMedications(medications.map((x, j) => j === i ? { ...x, frequency: v } : x))}>
                        <SelectTrigger aria-label="Frequency" className="w-full"><SelectValue placeholder="Frequency" /></SelectTrigger>
                        <SelectContent>{FREQUENCIES.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}</SelectContent>
                      </Select>
                      <Select value={m.action} onValueChange={(v) => setMedications(medications.map((x, j) => j === i ? { ...x, action: v as MedicationIn["action"] } : x))}>
                        <SelectTrigger aria-label="Action" className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>{ACTIONS.map((a) => <SelectItem key={a} value={a}>{titleCase(a)}</SelectItem>)}</SelectContent>
                      </Select>
                      <Button variant="ghost" size="icon" aria-label="Remove medication" onClick={() => setMedications(medications.filter((_, j) => j !== i))}><Trash2 /></Button>
                    </div>
                  ))}
                </div>
              </section>

              {activeMeds.length > 0 && (
                <section aria-labelledby="stop">
                  <h3 id="stop" className="mb-2 text-sm font-medium">Stop current medications</h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {activeMeds.map((m) => (
                      <label key={m.id} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm has-[:checked]:border-risk-high/50 has-[:checked]:bg-risk-high-soft">
                        <Checkbox checked={stopIds.includes(m.id)}
                                  onCheckedChange={(v) => setStopIds(v ? [...stopIds, m.id] : stopIds.filter((x) => x !== m.id))} />
                        <span><span className="font-medium">{m.name}</span> <span className="text-muted-foreground">{m.dose}</span></span>
                      </label>
                    ))}
                  </div>
                  <p className="mt-1.5 text-xs text-muted-foreground">Dose changes stop the old entry automatically; it’s pre-selected here.</p>
                </section>
              )}

              <section className="grid gap-2 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="fu">Follow-up date</Label>
                  <Input id="fu" type="date" value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
                </div>
              </section>

              <div className="flex flex-wrap items-center gap-2 border-t pt-4">
                <Button onClick={() => save.mutate()} disabled={save.isPending}>
                  {save.isPending && <Loader2 className="animate-spin" aria-hidden />} Save consultation
                </Button>
                <span className="text-xs text-muted-foreground">{itemCount} item{itemCount === 1 ? "" : "s"} · saved with the note and audited</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
