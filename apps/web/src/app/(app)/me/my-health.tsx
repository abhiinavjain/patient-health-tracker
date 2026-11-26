"use client";

import Link from "next/link";
import { ClipboardCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RoleGate } from "@/components/states";
import { PatientRecord } from "@/components/patient/patient-record";
import { useMe } from "@/lib/hooks";

export function MyHealth() {
  return <RoleGate roles={["patient"]}><Inner /></RoleGate>;
}

function Inner() {
  const { data: me } = useMe();
  if (!me?.patient_id) return null;
  return (
    <PatientRecord
      patientId={me.patient_id}
      audience="patient"
      bookHref="/me/appointments"
      actions={<Button asChild variant="outline"><Link href="/me/health-check"><ClipboardCheck aria-hidden /> Update health check</Link></Button>}
    />
  );
}
