"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState, PageHeader, RoleGate } from "@/components/states";
import { formatDate, pct } from "@/lib/format";
import { useModelMonitoring, useRiskModels } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const DRIFT = {
  stable: "bg-risk-low-soft text-risk-low border-risk-low/30",
  moderate: "bg-risk-moderate-soft text-risk-moderate border-risk-moderate/30",
  significant: "bg-risk-high-soft text-risk-high border-risk-high/30",
};

export function Models() {
  return <RoleGate roles={["admin"]}><Inner /></RoleGate>;
}

function Inner() {
  const mon = useModelMonitoring();
  const reg = useRiskModels();
  return (
    <>
      <PageHeader title="Model monitoring" description="Are live patients being scored like the population each model was validated on?" />
      {mon.isPending || reg.isPending ? <div className="grid gap-4 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-80" />)}</div> :
        mon.error ? <ErrorState error={mon.error} retry={mon.refetch} /> : (
        <div className="grid gap-4 lg:grid-cols-3">
          {mon.data.map((m) => {
            const info = reg.data?.find((r) => r.name === m.model);
            const top10 = info?.top_k.find((k) => Math.abs(k.fraction_flagged - 0.1) < 1e-6);
            return (
              <Card key={m.model}>
                <CardHeader>
                  <CardTitle className="text-base">{m.title}</CardTitle>
                  <CardDescription className="font-mono text-xs">{m.version}{info ? ` · trained ${formatDate(info.trained_at)}` : ""}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Score drift (PSI)</span>
                    {m.drift ? (
                      <Badge variant="outline" className={cn("tabular", DRIFT[m.drift])}>{m.psi?.toFixed(2)} · {m.drift}</Badge>
                    ) : <span className="text-xs text-muted-foreground">needs ≥ 20 live scores</span>}
                  </div>
                  <dl className="grid grid-cols-2 gap-3">
                    <div className="rounded-md bg-muted/60 p-2.5"><dt className="text-xs text-muted-foreground">Live scores</dt><dd className="tabular font-semibold">{m.live_scores}</dd></div>
                    <div className="rounded-md bg-muted/60 p-2.5"><dt className="text-xs text-muted-foreground">Test ROC-AUC</dt><dd className="tabular font-semibold">{m.test_roc_auc.toFixed(3)}</dd></div>
                    <div className="rounded-md bg-muted/60 p-2.5"><dt className="text-xs text-muted-foreground">Mean score (live)</dt><dd className="tabular font-semibold">{pct(m.live_mean_score, 1)}</dd></div>
                    <div className="rounded-md bg-muted/60 p-2.5"><dt className="text-xs text-muted-foreground">Mean score (validation)</dt><dd className="tabular font-semibold">{pct(m.reference_mean_score, 1)}</dd></div>
                  </dl>
                  {top10 && (
                    <p className="text-xs text-muted-foreground">
                      Flagging the top 10% catches {pct(top10.recall)} of events at {pct(top10.precision)} precision ({top10.lift.toFixed(1)}× random).
                    </p>
                  )}
                  {info && <p className="text-xs text-muted-foreground">{info.intended_use}</p>}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
      <p className="mt-4 max-w-3xl text-xs text-muted-foreground">
        PSI compares the distribution of live scores with the validation distribution across ten equal-mass bins. Below 0.1 is
        stable, 0.1–0.25 is a moderate shift, and above 0.25 needs investigation. The demo population is synthetic and deliberately
        sicker and older than the training data, so some drift is expected.
      </p>
    </>
  );
}
