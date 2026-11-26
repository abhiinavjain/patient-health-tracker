"use client";

import { useState } from "react";
import { Eye, ShieldCheck, ShieldOff, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { api } from "@/lib/api";
import { formatDate, formatDateTime, initials, titleCase } from "@/lib/format";
import { useClinicians, useGrants, useMe, usePatientAudit } from "@/lib/hooks";

const ACTION_TEXT: Record<string, string> = {
  view: "Viewed", create: "Added", update: "Updated", grant: "Access granted", revoke: "Access revoked", extract: "Analysed a note", risk: "Recalculated risk", signup: "Account created",
};

export function Privacy() {
  return <RoleGate roles={["patient"]}><Inner /></RoleGate>;
}

function Inner() {
  const { data: me } = useMe();
  const pid = me?.patient_id ?? "";
  const qc = useQueryClient();
  const grants = useGrants(pid);
  const audit = usePatientAudit(pid);
  const clinicians = useClinicians();
  const [pick, setPick] = useState("");
  const granted = new Set((grants.data ?? []).map((g) => g.clinician.id));

  const grant = useMutation({
    mutationFn: () => api(`/patients/${pid}/access`, { method: "POST", body: { clinician_id: pick } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["patient", pid] }); setPick(""); toast.success("Access granted"); },
    onError: (e) => toast.error(e.message),
  });
  const revoke = useMutation({
    mutationFn: (grantId: string) => api(`/patients/${pid}/access/${grantId}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["patient", pid] }); toast.success("Access revoked"); },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader title="Privacy & access" description="You decide which doctors can open your record. Every view and change is logged here." />
      <div className="grid gap-4 lg:grid-cols-[22rem_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="size-4 text-risk-low" aria-hidden /> Doctors with access</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {grants.isPending ? <LoadingRows rows={2} /> : (grants.data ?? []).length === 0 ? <EmptyState title="No one has access" text="Grant access to a doctor before your visit." /> :
              grants.data!.map((g) => (
                <div key={g.id} className="flex items-center gap-3">
                  <Avatar className="size-9"><AvatarFallback className="bg-primary/10 text-xs text-primary">{initials(g.clinician.full_name)}</AvatarFallback></Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{g.clinician.full_name}</p>
                    <p className="text-xs text-muted-foreground">{g.clinician.specialty} · since {formatDate(g.granted_at)}</p>
                  </div>
                  <Dialog>
                    <DialogTrigger asChild><Button variant="ghost" size="sm" aria-label={`Revoke access for ${g.clinician.full_name}`}><ShieldOff aria-hidden /></Button></DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Revoke access?</DialogTitle>
                        <DialogDescription>{g.clinician.full_name} will no longer be able to open your record. You can grant access again later.</DialogDescription>
                      </DialogHeader>
                      <DialogFooter>
                        <DialogClose asChild><Button variant="outline">Keep access</Button></DialogClose>
                        <DialogClose asChild><Button variant="destructive" onClick={() => revoke.mutate(g.id)}>Revoke</Button></DialogClose>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              ))}
            <div className="flex gap-2 border-t pt-3">
              <Select value={pick} onValueChange={setPick}>
                <SelectTrigger className="w-full" aria-label="Doctor to grant access"><SelectValue placeholder="Add a doctor" /></SelectTrigger>
                <SelectContent>
                  {(clinicians.data ?? []).filter((c) => !granted.has(c.id)).map((c) => <SelectItem key={c.id} value={c.id}>{c.full_name} — {c.specialty}</SelectItem>)}
                </SelectContent>
              </Select>
              <Button onClick={() => grant.mutate()} disabled={!pick || grant.isPending} aria-label="Grant access"><UserPlus aria-hidden /></Button>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><Eye className="size-4 text-muted-foreground" aria-hidden /> Who looked at my record</CardTitle>
            <CardDescription>The most recent 200 events.</CardDescription>
          </CardHeader>
          <CardContent className="px-0">
            {audit.isPending ? <div className="px-6"><LoadingRows /></div> : (
              <Table>
                <TableHeader><TableRow><TableHead className="pl-6">When</TableHead><TableHead>Who</TableHead><TableHead className="pr-6">What</TableHead></TableRow></TableHeader>
                <TableBody>
                  {(audit.data ?? []).map((e, i) => (
                    <TableRow key={i}>
                      <TableCell className="tabular pl-6 text-muted-foreground">{formatDateTime(e.at)}</TableCell>
                      <TableCell>
                        <span className="font-medium">{e.actor_name ?? "System"}</span>
                        {e.actor_role && <Badge variant="outline" className="ml-2 text-[10px]">{e.actor_role === "patient" ? "you" : e.actor_role}</Badge>}
                      </TableCell>
                      <TableCell className="pr-6 text-muted-foreground">{ACTION_TEXT[e.action] ?? titleCase(e.action)}{e.entity ? ` · ${titleCase(e.entity)}` : ""}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
