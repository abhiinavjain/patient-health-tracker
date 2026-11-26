"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, RoleGate } from "@/components/states";
import { api } from "@/lib/api";
import type { Patient } from "@/lib/types";

export function NewPatient() {
  return <RoleGate roles={["clinician"]}><Inner /></RoleGate>;
}

function Inner() {
  const router = useRouter();
  const qc = useQueryClient();
  const [f, setF] = useState({ full_name: "", date_of_birth: "", sex: "", blood_group: "", phone: "", address: "", emergency_contact: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const create = useMutation({
    mutationFn: () => api<Patient>("/patients", {
      method: "POST",
      body: Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v])),
    }),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["patients"] });
      toast.success(`${p.full_name} registered (${p.mrn})`);
      router.push(`/patients/${p.id}/consult`);
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader title="Register a patient" description="For walk-in patients without an account. You will be given access to their record automatically." />
      <Card className="max-w-2xl">
        <CardContent>
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <div className="space-y-2 sm:col-span-2"><Label htmlFor="n">Full name</Label><Input id="n" required value={f.full_name} onChange={set("full_name")} /></div>
            <div className="space-y-2"><Label htmlFor="dob">Date of birth</Label><Input id="dob" type="date" required value={f.date_of_birth} onChange={set("date_of_birth")} max={new Date().toISOString().slice(0, 10)} /></div>
            <div className="space-y-2">
              <Label htmlFor="sex">Sex</Label>
              <Select value={f.sex} onValueChange={(v) => setF({ ...f, sex: v })}>
                <SelectTrigger id="sex" className="w-full"><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent><SelectItem value="female">Female</SelectItem><SelectItem value="male">Male</SelectItem><SelectItem value="other">Other</SelectItem></SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="bg">Blood group</Label>
              <Select value={f.blood_group} onValueChange={(v) => setF({ ...f, blood_group: v })}>
                <SelectTrigger id="bg" className="w-full"><SelectValue placeholder="Unknown" /></SelectTrigger>
                <SelectContent>{["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label htmlFor="ph">Phone</Label><Input id="ph" type="tel" value={f.phone} onChange={set("phone")} /></div>
            <div className="space-y-2 sm:col-span-2"><Label htmlFor="ad">Address</Label><Input id="ad" value={f.address} onChange={set("address")} /></div>
            <div className="space-y-2 sm:col-span-2"><Label htmlFor="ec">Emergency contact</Label><Input id="ec" value={f.emergency_contact} onChange={set("emergency_contact")} /></div>
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" disabled={create.isPending || !f.sex}>{create.isPending && <Loader2 className="animate-spin" aria-hidden />} Register and start consultation</Button>
              <Button type="button" variant="ghost" onClick={() => router.back()}>Cancel</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </>
  );
}
