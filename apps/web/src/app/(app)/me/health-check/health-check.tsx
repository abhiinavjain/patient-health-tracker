"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { keys, useLifestyle, useMe } from "@/lib/hooks";
import type { Lifestyle } from "@/lib/types";

const YES_NO: { key: keyof Lifestyle; q: string; hint?: string }[] = [
  { key: "smoker", q: "Have you smoked at least 100 cigarettes in your life?", hint: "About 5 packs. Include past smoking." },
  { key: "phys_activity", q: "Did you do any physical activity or exercise in the past 30 days, other than your job?" },
  { key: "fruits_daily", q: "Do you eat fruit at least once a day?" },
  { key: "veggies_daily", q: "Do you eat vegetables at least once a day?" },
  { key: "heavy_alcohol", q: "Do you drink heavily?", hint: "More than 14 drinks a week for men, 7 for women." },
  { key: "difficulty_walking", q: "Do you have serious difficulty walking or climbing stairs?" },
];
const HEALTH = ["Excellent", "Very good", "Good", "Fair", "Poor"];
const EMPTY: Lifestyle = { smoker: null, phys_activity: null, fruits_daily: null, veggies_daily: null, heavy_alcohol: null,
  general_health: null, poor_mental_health_days: null, poor_physical_health_days: null, difficulty_walking: null };

export function HealthCheck() {
  return <RoleGate roles={["patient"]}><Inner /></RoleGate>;
}

function Inner() {
  const { data: me } = useMe();
  const pid = me?.patient_id ?? "";
  const history = useLifestyle(pid);
  if (history.isPending) return <LoadingRows rows={5} />;
  const last = history.data?.[0];
  // Mount the form once the previous answers are known, so they become its initial state.
  return <Form key={last?.id ?? "new"} pid={pid} last={last} />;
}

function Form({ pid, last }: { pid: string; last?: Lifestyle }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [a, setA] = useState<Lifestyle>(() => ({ ...EMPTY, ...(last ?? {}) }));

  const save = useMutation({
    mutationFn: () => api(`/patients/${pid}/lifestyle`, { method: "POST", body: Object.fromEntries(Object.entries(a).filter(([k]) => k in EMPTY)) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.patient(pid) });
      toast.success("Thanks — your risk estimates have been updated");
      router.push("/me");
    },
    onError: (e) => toast.error(e.message),
  });
  const answered = Object.values(a).filter((v) => v !== null).length;

  return (
    <>
      <PageHeader title="Health check" description={`Nine quick questions. Your answers help estimate your diabetes and heart-disease risk.${last?.recorded_at ? ` Last updated ${formatDate(last.recorded_at)}.` : ""}`} />
      <form className="max-w-2xl space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Overall, how would you rate your health?</CardTitle>
          </CardHeader>
          <CardContent>
            <RadioGroup value={a.general_health ? String(a.general_health) : ""} onValueChange={(v) => setA({ ...a, general_health: Number(v) })}
                        className="grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="General health">
              {HEALTH.map((h, i) => (
                <Label key={h} className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 font-normal has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5">
                  <RadioGroupItem value={String(i + 1)} /> {h}
                </Label>
              ))}
            </RadioGroup>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Your habits</CardTitle><CardDescription>Choose yes or no.</CardDescription></CardHeader>
          <CardContent className="divide-y">
            {YES_NO.map(({ key, q, hint }) => (
              <fieldset key={key} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                <legend className="sr-only">{q}</legend>
                <div className="text-sm">
                  <p>{q}</p>
                  {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
                </div>
                <RadioGroup value={a[key] === null ? "" : a[key] ? "yes" : "no"} onValueChange={(v) => setA({ ...a, [key]: v === "yes" })}
                            className="flex shrink-0 gap-2" aria-label={q}>
                  {["yes", "no"].map((v) => (
                    <Label key={v} className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-1.5 font-normal capitalize has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5">
                      <RadioGroupItem value={v} /> {v}
                    </Label>
                  ))}
                </RadioGroup>
              </fieldset>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">In the past 30 days…</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            {([["poor_physical_health_days", "Days your physical health was not good"], ["poor_mental_health_days", "Days your mental health was not good"]] as const).map(([k, label]) => (
              <div key={k} className="space-y-2">
                <Label htmlFor={k}>{label}</Label>
                <Input id={k} type="number" min={0} max={30} value={a[k] ?? ""} onChange={(e) => setA({ ...a, [k]: e.target.value === "" ? null : Math.min(30, Math.max(0, e.target.valueAsNumber)) })} />
              </div>
            ))}
          </CardContent>
        </Card>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={save.isPending || answered < 5}>{save.isPending && <Loader2 className="animate-spin" aria-hidden />} Save answers</Button>
          <span className="text-xs text-muted-foreground">{answered}/9 answered · visible to doctors you’ve granted access</span>
        </div>
      </form>
    </>
  );
}
