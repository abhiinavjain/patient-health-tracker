"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/states";
import { formatDate, OBSERVATIONS, REFERENCE } from "@/lib/format";
import { useSeries } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const PANELS = [
  { id: "bp", label: "Blood pressure", codes: ["bp_systolic", "bp_diastolic"], ref: "bp_systolic" },
  { id: "hba1c", label: "HbA1c", codes: ["hba1c"], ref: "hba1c" },
  { id: "weight", label: "Weight", codes: ["weight"], ref: null },
  { id: "ldl", label: "LDL cholesterol", codes: ["ldl"], ref: "ldl" },
  { id: "kidney", label: "Kidney (eGFR)", codes: ["egfr"], ref: "egfr" },
] as const;

const COLORS = ["var(--chart-1)", "var(--chart-4)"];

export function TrendChart({ patientId, compact = false }: { patientId: string; compact?: boolean }) {
  const [panel, setPanel] = useState<(typeof PANELS)[number]>(PANELS[0]);
  const { data, isPending } = useSeries(patientId, [...panel.codes]);

  const rows = useMemo(() => {
    const byTime = new Map<string, Record<string, number | string>>();
    for (const s of data ?? [])
      for (const p of s.points) {
        const key = p.observed_at.slice(0, 10);
        const row = byTime.get(key) ?? { date: key };
        row[s.code] = p.value;
        byTime.set(key, row);
      }
    return [...byTime.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [data]);

  const ref = panel.ref ? REFERENCE[panel.ref] : null;
  const unit = OBSERVATIONS[panel.codes[0]]?.unit;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 pb-2 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle className="text-base">Trends</CardTitle>
        <div role="tablist" aria-label="Measurement" className="flex flex-wrap gap-1">
          {PANELS.map((p) => (
            <button
              key={p.id}
              role="tab"
              aria-selected={p.id === panel.id}
              onClick={() => setPanel(p)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                p.id === panel.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:text-foreground",
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <Skeleton className={compact ? "h-48" : "h-72"} />
        ) : rows.length === 0 ? (
          <EmptyState title={`No ${panel.label.toLowerCase()} readings yet`} />
        ) : (
          <div className={compact ? "h-48" : "h-72"}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                {ref && <ReferenceArea y1={ref[0]} y2={ref[1]} fill="var(--risk-low)" fillOpacity={0.07} ifOverflow="extendDomain" />}
                <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                       tickLine={false} axisLine={false} minTickGap={24} />
                <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={44}
                       domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                  labelFormatter={(d) => formatDate(String(d))}
                  formatter={(v, name) => [`${v} ${unit ?? ""}`, OBSERVATIONS[String(name)]?.label ?? String(name)]}
                />
                {panel.codes.length > 1 && (
                  <Legend formatter={(v) => <span className="text-xs text-muted-foreground">{OBSERVATIONS[String(v)]?.label}</span>} />
                )}
                {panel.codes.map((c, i) => (
                  <Line key={c} type="monotone" dataKey={c} stroke={COLORS[i]} strokeWidth={2} dot={{ r: 2.5 }}
                        activeDot={{ r: 4 }} connectNulls isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        {ref && rows.length > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            Shaded band: typical adult range ({ref[0]}–{ref[1]} {unit}).
          </p>
        )}
      </CardContent>
    </Card>
  );
}
