"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, FilePlus2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { RoleGate } from "@/components/states";
import { PatientRecord } from "@/components/patient/patient-record";
import { api } from "@/lib/api";
import { keys } from "@/lib/hooks";

export function PatientChart() {
  return <RoleGate roles={["clinician"]}><Inner /></RoleGate>;
}

function Inner() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const recompute = useMutation({
    mutationFn: () => api(`/patients/${id}/risk/recompute`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.patient(id) });
      qc.invalidateQueries({ queryKey: ["worklist"] });
      toast.success("Risk scores recalculated");
    },
  });
  return (
    <>
      <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2 text-muted-foreground">
        <Link href="/patients"><ArrowLeft aria-hidden /> Patients</Link>
      </Button>
      <PatientRecord
        patientId={id}
        audience="clinician"
        actions={
          <>
            <Button variant="outline" onClick={() => recompute.mutate()} disabled={recompute.isPending}>
              <RefreshCw className={recompute.isPending ? "animate-spin" : ""} aria-hidden /> Recalculate risk
            </Button>
            <Button asChild><Link href={`/patients/${id}/consult`}><FilePlus2 aria-hidden /> New consultation</Link></Button>
          </>
        }
      />
    </>
  );
}
