"use client";

import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, CircleSlash, Info, ClipboardCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { BAND_BAR, BAND_CLASS, BAND_LABEL, MODEL_SHORT, pct } from "@/lib/format";
import { useRiskModels } from "@/lib/hooks";
import type { Band, RiskResult } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RiskBadge({ band, className }: { band: Band; className?: string }) {
  return (
    <Badge variant="outline" className={cn("font-medium", BAND_CLASS[band], className)}>
      {BAND_LABEL[band]} risk
    </Badge>
  );
}

function ModelInfo({ model }: { model: string }) {
  const { data } = useRiskModels();
  const m = data?.find((x) => x.name === model);
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="size-7 text-muted-foreground" aria-label="About this model">
          <Info className="size-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{m?.title ?? "About this model"}</DialogTitle>
          <DialogDescription>{m?.target}</DialogDescription>
        </DialogHeader>
        {m && (
          <div className="space-y-4 text-sm">
            <p>{m.intended_use}</p>
            <dl className="grid grid-cols-3 gap-3 rounded-lg bg-muted p-3 text-center">
              <div><dt className="text-xs text-muted-foreground">ROC-AUC</dt><dd className="tabular font-semibold">{m.metrics.roc_auc.toFixed(2)}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Base rate</dt><dd className="tabular font-semibold">{pct(m.metrics.prevalence, 1)}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Brier</dt><dd className="tabular font-semibold">{m.metrics.brier.toFixed(3)}</dd></div>
            </dl>
            <div>
              <p className="mb-1 font-medium">Limitations</p>
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {m.limitations.map((l) => <li key={l}>{l}</li>)}
              </ul>
            </div>
            <p className="text-xs text-muted-foreground">Version {m.version} · decision support only — not a diagnosis.</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function RiskCard({ risk, audience = "clinician" }: { risk: RiskResult; audience?: "clinician" | "patient" }) {
  const short = MODEL_SHORT[risk.model] ?? risk.title;
  const header = (
    <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
      <div className="space-y-1">
        <CardTitle className="text-base">{risk.title}</CardTitle>
        {risk.status === "scored" && risk.band && <RiskBadge band={risk.band} />}
      </div>
      <ModelInfo model={risk.model} />
    </CardHeader>
  );

  if (risk.status === "not_applicable")
    return (
      <Card className="bg-muted/40">
        {header}
        <CardContent className="flex gap-2 text-sm text-muted-foreground">
          <CircleSlash className="mt-0.5 size-4 shrink-0" aria-hidden />
          <p>{risk.reason}</p>
        </CardContent>
      </Card>
    );

  if (risk.status === "insufficient_data")
    return (
      <Card className="border-dashed">
        {header}
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            {audience === "patient"
              ? `We need a few more answers to estimate your ${short.toLowerCase()} risk.`
              : `Not enough data recorded for a reliable ${short.toLowerCase()} score.`}
          </p>
          {risk.missing_inputs.length > 0 && (
            <p className="text-xs text-muted-foreground">Missing: {risk.missing_inputs.slice(0, 6).join(", ")}{risk.missing_inputs.length > 6 ? "…" : ""}</p>
          )}
          {audience === "patient" && (
            <Button asChild size="sm"><Link href="/me/health-check"><ClipboardCheck aria-hidden /> Complete health check</Link></Button>
          )}
        </CardContent>
      </Card>
    );

  const score = risk.score ?? 0;
  const band = risk.band ?? "low";
  const maxImpact = Math.max(...risk.factors.map((f) => Math.abs(f.impact)), 0.01);
  return (
    <Card>
      {header}
      <CardContent className="space-y-4">
        <div>
          <p className="tabular text-3xl font-semibold tracking-tight">{pct(score)}</p>
          <p className="text-sm text-muted-foreground">
            {audience === "patient" ? "estimated risk" : "predicted probability"} · higher than {risk.percentile}% of the reference group
          </p>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted" role="img"
               aria-label={`Risk percentile ${risk.percentile} of 100`}>
            <div className={cn("h-full rounded-full", BAND_BAR[band])} style={{ width: `${Math.max(3, risk.percentile ?? 0)}%` }} />
          </div>
        </div>
        {risk.factors.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">What drives this</p>
            <ul className="space-y-2">
              {risk.factors.map((f) => {
                const up = f.direction === "increases";
                return (
                  <li key={f.feature} className="grid grid-cols-[1rem_1fr_auto] items-center gap-2 text-sm">
                    {up ? <ArrowUpRight className="size-4 text-risk-high" aria-label="increases risk" />
                        : <ArrowDownRight className="size-4 text-risk-low" aria-label="decreases risk" />}
                    <span className="min-w-0 truncate" title={`${f.label}: ${f.display_value}`}>
                      {f.label}: <span className="font-medium">{f.display_value}</span>
                    </span>
                    <span className="h-1.5 w-14 overflow-hidden rounded-full bg-muted" aria-hidden>
                      <span className={cn("block h-full rounded-full", up ? "bg-risk-high/70" : "bg-risk-low/70")}
                            style={{ width: `${(Math.abs(f.impact) / maxImpact) * 100}%` }} />
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        {risk.completeness != null && risk.completeness < 1 && (
          <p className="text-xs text-muted-foreground">
            Based on {Math.round(risk.completeness * 100)}% of inputs; missing values were filled with typical values.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
