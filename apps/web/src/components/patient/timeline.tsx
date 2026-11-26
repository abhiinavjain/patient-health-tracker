"use client";

import { useMemo, useState } from "react";
import { Activity, AlertOctagon, Gauge, Hospital, Pill, Stethoscope, Siren, Video } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { formatDate, formatDateTime, OBSERVATIONS, outOfRange, titleCase } from "@/lib/format";
import { useEncounter, useTimeline } from "@/lib/hooks";
import type { TimelineEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const KINDS: { id: TimelineEvent["kind"] | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "encounter", label: "Visits" },
  { id: "condition", label: "Diagnoses" },
  { id: "medication", label: "Medications" },
  { id: "observation", label: "Home readings" },
];

function EventIcon({ e }: { e: TimelineEvent }) {
  const t = e.title.toLowerCase();
  const Icon =
    e.kind === "encounter"
      ? t.startsWith("inpatient") ? Hospital : t.startsWith("emergency") ? Siren : t.startsWith("telehealth") ? Video : Stethoscope
      : e.kind === "medication" ? Pill : e.kind === "allergy" ? AlertOctagon : e.kind === "observation" ? Gauge : Activity;
  const tone =
    e.kind === "encounter" && (t.startsWith("inpatient") || t.startsWith("emergency"))
      ? "bg-risk-high-soft text-risk-high" : e.kind === "encounter" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground";
  return <span className={cn("grid size-8 shrink-0 place-items-center rounded-full", tone)}><Icon className="size-4" aria-hidden /></span>;
}

function EncounterDialog({ patientId, encounterId, onClose }: { patientId: string; encounterId: string | null; onClose: () => void }) {
  const { data: e, isPending, error } = useEncounter(patientId, encounterId);
  return (
    <Dialog open={!!encounterId} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[85svh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{e ? `${titleCase(e.type)} visit` : "Visit"}</DialogTitle>
          <DialogDescription>
            {e ? `${formatDateTime(e.started_at)}${e.ended_at && e.type === "inpatient" ? ` – ${formatDate(e.ended_at)}` : ""}${e.clinician ? ` · ${e.clinician.full_name}` : ""}` : " "}
          </DialogDescription>
        </DialogHeader>
        {isPending ? <Skeleton className="h-40" /> : error ? <ErrorState error={error} /> : e && (
          <div className="space-y-5 text-sm">
            {e.reason && <p><span className="text-muted-foreground">Reason: </span>{e.reason}</p>}
            {e.type === "inpatient" && (
              <p className="text-muted-foreground">
                {[e.admission_type && `${titleCase(e.admission_type)} admission`, e.admission_source && `from ${titleCase(e.admission_source)}`,
                  e.discharge_disposition && `discharged to ${titleCase(e.discharge_disposition)}`].filter(Boolean).join(" · ")}
              </p>
            )}
            {e.conditions.length > 0 && (
              <section>
                <h3 className="mb-2 font-medium">Diagnoses</h3>
                <ul className="space-y-1">
                  {e.conditions.map((c) => (
                    <li key={c.id} className="flex items-center gap-2">
                      <Badge variant="secondary" className="font-mono text-[11px]">{c.icd10_code}</Badge>
                      {c.description}{c.is_primary && <span className="text-xs text-muted-foreground">(primary)</span>}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {e.observations.length > 0 && (
              <section>
                <h3 className="mb-2 font-medium">Measurements</h3>
                <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {e.observations.map((o) => (
                    <div key={o.id} className="rounded-md bg-muted/60 px-2.5 py-1.5">
                      <dt className="text-xs text-muted-foreground">{OBSERVATIONS[o.code]?.label ?? o.code}</dt>
                      <dd className={cn("tabular font-medium", outOfRange(o.code, o.value) && "text-risk-high")}>{o.value} <span className="text-xs font-normal text-muted-foreground">{o.unit}</span></dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}
            {e.medications.length > 0 && (
              <section>
                <h3 className="mb-2 font-medium">Medication changes</h3>
                <ul className="space-y-1">
                  {e.medications.map((m) => (
                    <li key={m.id}><Badge variant="outline" className="mr-2">{titleCase(m.action)}</Badge>{m.name} <span className="text-muted-foreground">{[m.dose, m.frequency].filter(Boolean).join(" · ")}</span></li>
                  ))}
                </ul>
              </section>
            )}
            {e.notes && (
              <section>
                <h3 className="mb-2 font-medium">Clinical note</h3>
                <p className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 font-mono text-xs leading-relaxed">{e.notes}</p>
              </section>
            )}
            {e.follow_up_date && <p className="text-muted-foreground">Follow-up planned {formatDate(e.follow_up_date)}</p>}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function Timeline({ patientId }: { patientId: string }) {
  const { data, isPending, error, refetch } = useTimeline(patientId);
  const [kind, setKind] = useState<(typeof KINDS)[number]["id"]>("all");
  const [open, setOpen] = useState<string | null>(null);
  const [limit, setLimit] = useState(40);

  const groups = useMemo(() => {
    const events = (data ?? []).filter((e) => kind === "all" || e.kind === kind).slice(0, limit);
    const out: { label: string; events: TimelineEvent[] }[] = [];
    for (const e of events) {
      const label = new Date(e.at).toLocaleDateString("en-IN", { month: "long", year: "numeric" });
      if (out.at(-1)?.label !== label) out.push({ label, events: [] });
      out.at(-1)!.events.push(e);
    }
    return out;
  }, [data, kind, limit]);
  const total = (data ?? []).filter((e) => kind === "all" || e.kind === kind).length;

  if (isPending) return <LoadingRows rows={6} />;
  if (error) return <ErrorState error={error} retry={refetch} />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1" role="tablist" aria-label="Filter history">
        {KINDS.map((k) => (
          <Button key={k.id} size="sm" variant={kind === k.id ? "default" : "outline"} role="tab" aria-selected={kind === k.id}
                  onClick={() => setKind(k.id)}>{k.label}</Button>
        ))}
      </div>
      {groups.length === 0 ? <EmptyState title="Nothing here yet" /> : (
        <ol className="space-y-6">
          {groups.map((g) => (
            <li key={g.label}>
              <h3 className="sticky top-14 z-10 mb-3 bg-background/90 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground backdrop-blur">{g.label}</h3>
              <ol className="relative space-y-3 border-l pl-6 ml-4">
                {g.events.map((e, i) => {
                  const clickable = e.kind === "encounter" && e.encounter_id;
                  const body = (
                    <>
                      <span className="absolute -left-10 top-0.5"><EventIcon e={e} /></span>
                      <span className="block text-sm font-medium">{e.title}</span>
                      {e.detail && <span className="block text-sm text-muted-foreground">{e.detail}</span>}
                      <span className="block text-xs text-muted-foreground">{formatDate(e.at)}</span>
                    </>
                  );
                  return (
                    <li key={`${e.kind}-${e.ref_id}-${i}`} className="relative min-h-8">
                      {clickable ? (
                        <button onClick={() => setOpen(e.encounter_id)} className="block w-full rounded-md text-left transition-colors hover:bg-accent/60 focus-visible:outline-2 focus-visible:outline-ring -mx-2 px-2 py-1">
                          {body}
                        </button>
                      ) : <div className="py-1">{body}</div>}
                    </li>
                  );
                })}
              </ol>
            </li>
          ))}
        </ol>
      )}
      {total > limit && <Button variant="outline" className="w-full" onClick={() => setLimit(limit + 40)}>Show older history</Button>}
      <EncounterDialog patientId={patientId} encounterId={open} onClose={() => setOpen(null)} />
    </div>
  );
}
