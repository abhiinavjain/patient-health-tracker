"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ErrorState, LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { formatDateTime, titleCase } from "@/lib/format";
import { useAdminAudit } from "@/lib/hooks";

const ACTIONS = ["all", "view", "create", "update", "grant", "revoke", "extract", "login", "risk"];

export function Audit() {
  return <RoleGate roles={["admin"]}><Inner /></RoleGate>;
}

function Inner() {
  const [action, setAction] = useState("all");
  const { data, isPending, error, refetch } = useAdminAudit(action === "all" ? undefined : action);
  return (
    <>
      <PageHeader
        title="Audit log"
        description="Append-only record of every chart view and change."
        actions={
          <Select value={action} onValueChange={setAction}>
            <SelectTrigger className="w-44" aria-label="Filter by action"><SelectValue /></SelectTrigger>
            <SelectContent>{ACTIONS.map((a) => <SelectItem key={a} value={a}>{a === "all" ? "All actions" : titleCase(a)}</SelectItem>)}</SelectContent>
          </Select>
        }
      />
      <Card className="py-0">
        {isPending ? <div className="p-4"><LoadingRows rows={10} /></div> : error ? <div className="p-4"><ErrorState error={error} retry={refetch} /></div> : (
          <Table>
            <TableHeader><TableRow><TableHead className="pl-6">When</TableHead><TableHead>Actor</TableHead><TableHead>Action</TableHead><TableHead>Entity</TableHead><TableHead className="pr-6 hidden md:table-cell">Patient</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.map((e, i) => (
                <TableRow key={i}>
                  <TableCell className="tabular pl-6 text-muted-foreground">{formatDateTime(e.at)}</TableCell>
                  <TableCell><span className="font-medium">{e.actor_name ?? "System"}</span>{e.actor_role && <Badge variant="outline" className="ml-2 text-[10px]">{e.actor_role}</Badge>}</TableCell>
                  <TableCell>{titleCase(e.action)}</TableCell>
                  <TableCell className="text-muted-foreground">{e.entity ? titleCase(e.entity) : "—"}</TableCell>
                  <TableCell className="pr-6 hidden font-mono text-xs text-muted-foreground md:table-cell">{e.patient_id ? `${e.patient_id.slice(0, 8)}…` : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </>
  );
}
