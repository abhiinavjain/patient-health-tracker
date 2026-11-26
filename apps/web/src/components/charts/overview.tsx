"use client";

import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/states";
import { formatMonth, MODEL_SHORT, pct } from "@/lib/format";
import { useOverview } from "@/lib/hooks";
import type { Band } from "@/lib/types";

const tooltipStyle = { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 };
const axis = { tick: { fontSize: 11, fill: "var(--muted-foreground)" }, tickLine: false, axisLine: false } as const;
const TYPE_COLORS = { outpatient: "var(--chart-1)", telehealth: "var(--chart-2)", emergency: "var(--chart-3)", inpatient: "var(--chart-4)" };
const BAND_COLORS: Record<Band, string> = { low: "var(--risk-low)", moderate: "var(--risk-moderate)", high: "var(--risk-high)" };

function Kpi({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Card className="gap-1 py-4">
      <CardContent className="px-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="tabular text-2xl font-semibold">{value}</p>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export function OverviewDashboard() {
  const { data, isPending, error, refetch } = useOverview(12);
  if (isPending) return <div className="grid gap-4 md:grid-cols-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-72" />)}</div>;
  if (error) return <ErrorState error={error} retry={refetch} />;

  const discharges = data.readmissions_by_month.reduce((s, r) => s + r.discharges, 0);
  const readmits = data.readmissions_by_month.reduce((s, r) => s + r.readmitted_30d, 0);
  const encounters = data.encounters_by_month.map((r) => ({ ...r, label: formatMonth(r.month) }));
  const readmitRows = data.readmissions_by_month.filter((r) => r.discharges > 0).map((r) => ({ ...r, label: formatMonth(r.month), ratePct: r.rate == null ? null : +(r.rate * 100).toFixed(1) }));
  const bands = Object.entries(data.risk_bands).map(([m, b]) => ({ model: MODEL_SHORT[m] ?? m, ...b }));
  const maxCond = Math.max(...data.top_conditions.map((c) => c.patients), 1);
  const totalAge = Object.values(data.age_bands).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label={data.scope === "population" ? "Patients" : "Patients on your panel"} value={data.totals.patients} />
        <Kpi label="Encounters" value={data.totals.encounters.toLocaleString()} hint="all time" />
        <Kpi label="Inpatient stays" value={data.totals.inpatient_stays} hint="all time" />
        <Kpi label="30-day readmission rate" value={pct(discharges ? readmits / discharges : null, 1)} hint={`${readmits} of ${discharges} discharges, last 12 months`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Encounters by month</CardTitle><CardDescription>By visit type, last 12 months</CardDescription></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={encounters} margin={{ left: -16, right: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="label" {...axis} minTickGap={8} />
                <YAxis {...axis} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--muted)" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {(Object.keys(TYPE_COLORS) as (keyof typeof TYPE_COLORS)[]).map((t) => (
                  <Bar key={t} dataKey={t} stackId="a" fill={TYPE_COLORS[t]} name={t[0].toUpperCase() + t.slice(1)} isAnimationActive={false} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Observed 30-day readmissions</CardTitle><CardDescription>Share of discharges followed by another admission within 30 days</CardDescription></CardHeader>
          <CardContent className="h-64">
            {readmitRows.length === 0 ? <p className="text-sm text-muted-foreground">No discharges in this period.</p> : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={readmitRows} margin={{ left: -16, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" {...axis} />
                  <YAxis {...axis} unit="%" domain={[0, "auto"]} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v, n) => (n === "ratePct" ? [`${v}%`, "Readmission rate"] : [v, String(n)])} />
                  <Line type="monotone" dataKey="ratePct" stroke="var(--chart-4)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Latest risk scores</CardTitle><CardDescription>Patients by band, per model</CardDescription></CardHeader>
          <CardContent className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bands} layout="vertical" margin={{ left: 8, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" {...axis} allowDecimals={false} />
                <YAxis type="category" dataKey="model" {...axis} width={92} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--muted)" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {(["low", "moderate", "high"] as Band[]).map((b) => (
                  <Bar key={b} dataKey={b} stackId="b" fill={BAND_COLORS[b]} name={b[0].toUpperCase() + b.slice(1)} isAnimationActive={false} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Most common active conditions</CardTitle><CardDescription>Patients with each problem-list diagnosis</CardDescription></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.top_conditions.slice(0, 8).map((c) => (
                <li key={c.icd10_code} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 text-sm">
                  <span className="truncate">{c.description} <span className="font-mono text-xs text-muted-foreground">{c.icd10_code}</span></span>
                  <span className="tabular text-xs text-muted-foreground">{c.patients}</span>
                  <span className="col-span-2 h-1.5 overflow-hidden rounded-full bg-muted">
                    <span className="block h-full rounded-full bg-chart-1" style={{ width: `${(c.patients / maxCond) * 100}%` }} />
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-5 grid grid-cols-4 gap-2 border-t pt-4 text-center">
              {Object.entries(data.age_bands).map(([band, n]) => (
                <div key={band}>
                  <p className="tabular text-sm font-semibold">{Math.round((n / totalAge) * 100)}%</p>
                  <p className="text-[11px] text-muted-foreground">age {band}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
