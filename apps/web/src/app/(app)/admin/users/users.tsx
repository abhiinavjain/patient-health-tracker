"use client";

import { useState } from "react";
import { Loader2, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ErrorState, LoadingRows, PageHeader, RoleGate } from "@/components/states";
import { api } from "@/lib/api";
import { titleCase } from "@/lib/format";
import { useAdminUsers, useMe } from "@/lib/hooks";

export function Users() {
  return <RoleGate roles={["admin"]}><Inner /></RoleGate>;
}

function NewStaff() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ full_name: "", email: "", password: "", role: "clinician", specialty: "" });
  const create = useMutation({
    mutationFn: () => api("/admin/users", { method: "POST", body: { ...f, specialty: f.specialty || null } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-users"] }); toast.success("Account created"); setOpen(false); setF({ full_name: "", email: "", password: "", role: "clinician", specialty: "" }); },
    onError: (e) => toast.error(e.message),
  });
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button><UserPlus aria-hidden /> Add staff</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Add a staff account</DialogTitle><DialogDescription>Patients register themselves; staff accounts are created here.</DialogDescription></DialogHeader>
        <form id="staff" className="grid gap-3" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <div className="space-y-2"><Label htmlFor="sn">Full name</Label><Input id="sn" required value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></div>
          <div className="space-y-2"><Label htmlFor="se">Email</Label><Input id="se" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
          <div className="space-y-2"><Label htmlFor="sp">Temporary password</Label><Input id="sp" type="password" minLength={10} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="sr">Role</Label>
              <Select value={f.role} onValueChange={(v) => setF({ ...f, role: v })}>
                <SelectTrigger id="sr" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="clinician">Clinician</SelectItem><SelectItem value="admin">Admin</SelectItem></SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label htmlFor="ss">Specialty</Label><Input id="ss" value={f.specialty} disabled={f.role !== "clinician"} onChange={(e) => setF({ ...f, specialty: e.target.value })} /></div>
          </div>
        </form>
        <DialogFooter><Button type="submit" form="staff" disabled={create.isPending}>{create.isPending && <Loader2 className="animate-spin" aria-hidden />} Create account</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Inner() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const { data, isPending, error, refetch } = useAdminUsers();
  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api(`/admin/users/${id}`, { method: "PATCH", body: { is_active } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-users"] }); toast.success("Account updated"); },
    onError: (e) => toast.error(e.message),
  });
  return (
    <>
      <PageHeader title="Users" description="Deactivated accounts lose access immediately." actions={<NewStaff />} />
      <Card className="py-0">
        {isPending ? <div className="p-4"><LoadingRows rows={8} /></div> : error ? <div className="p-4"><ErrorState error={error} retry={refetch} /></div> : (
          <Table>
            <TableHeader><TableRow><TableHead className="pl-6">Name</TableHead><TableHead className="hidden sm:table-cell">Email</TableHead><TableHead>Role</TableHead><TableHead>Status</TableHead><TableHead className="pr-6 text-right">Action</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="pl-6 font-medium">{u.full_name}{u.specialty && <span className="block text-xs font-normal text-muted-foreground">{u.specialty}</span>}</TableCell>
                  <TableCell className="hidden text-muted-foreground sm:table-cell">{u.email}</TableCell>
                  <TableCell><Badge variant="outline">{titleCase(u.role)}</Badge></TableCell>
                  <TableCell><Badge variant={u.is_active ? "default" : "secondary"}>{u.is_active ? "Active" : "Deactivated"}</Badge></TableCell>
                  <TableCell className="pr-6 text-right">
                    {u.id !== me?.id && (
                      <Button size="sm" variant="ghost" onClick={() => toggle.mutate({ id: u.id, is_active: !u.is_active })}>{u.is_active ? "Deactivate" : "Reactivate"}</Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </>
  );
}
