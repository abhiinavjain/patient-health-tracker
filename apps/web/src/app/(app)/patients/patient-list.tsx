"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDeferredValue, useState } from "react";
import { Search, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { RiskBadge } from "@/components/risk/risk-card";
import { MODEL_SHORT, relative } from "@/lib/format";
import { usePatients } from "@/lib/hooks";

export function PatientList() {
  return <RoleGate roles={["clinician"]}><Inner /></RoleGate>;
}

function Inner() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const deferred = useDeferredValue(q.trim());
  const { data, isPending, error, refetch } = usePatients(deferred);

  return (
    <>
      <PageHeader
        title="Patients"
        description="Only patients who have granted you access are listed."
        actions={<Button asChild><Link href="/patients/new"><UserPlus aria-hidden /> Register patient</Link></Button>}
      />
      <div className="relative mb-4 max-w-md">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or MRN" className="pl-9" aria-label="Search patients" />
      </div>
      <Card className="py-0">
        {isPending ? <div className="p-4"><LoadingRows rows={8} /></div> : error ? <div className="p-4"><ErrorState error={error} retry={refetch} /></div> :
          data.length === 0 ? <div className="p-4"><EmptyState title={deferred ? "No matching patients" : "No patients yet"} /></div> : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Name</TableHead><TableHead>Age / sex</TableHead>
                <TableHead className="hidden md:table-cell">MRN</TableHead><TableHead className="hidden sm:table-cell">Last visit</TableHead>
                <TableHead className="pr-6">Risk flags</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((p) => {
                const flags = Object.entries(p.latest_risk).filter(([, b]) => b !== "low");
                return (
                  <TableRow key={p.id} className="cursor-pointer" onClick={() => router.push(`/patients/${p.id}`)}>
                    <TableCell className="pl-6 font-medium">
                      <Link href={`/patients/${p.id}`} className="hover:underline" onClick={(e) => e.stopPropagation()}>{p.full_name}</Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{p.age} · {p.sex[0].toUpperCase()}</TableCell>
                    <TableCell className="hidden font-mono text-xs text-muted-foreground md:table-cell">{p.mrn}</TableCell>
                    <TableCell className="hidden text-muted-foreground sm:table-cell">{relative(p.last_encounter_at)}</TableCell>
                    <TableCell className="pr-6">
                      <div className="flex flex-wrap gap-1">
                        {flags.length === 0 ? <span className="text-xs text-muted-foreground">—</span> : flags.map(([m, b]) => (
                          <span key={m} className="inline-flex items-center gap-1 text-xs">
                            <RiskBadge band={b} className="px-1.5" /><span className="text-muted-foreground">{MODEL_SHORT[m]}</span>
                          </span>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Card>
    </>
  );
}
