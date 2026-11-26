"use client";

import { useParams } from "next/navigation";
import { RoleGate } from "@/components/states";
import { ConsultWorkspace } from "@/components/consult/consult-workspace";

export function Consult() {
  const { id } = useParams<{ id: string }>();
  return <RoleGate roles={["clinician"]}><ConsultWorkspace patientId={id} /></RoleGate>;
}
