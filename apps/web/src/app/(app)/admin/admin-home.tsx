"use client";

import { OverviewDashboard } from "@/components/charts/overview";
import { PageHeader, RoleGate } from "@/components/states";

export function AdminHome() {
  return (
    <RoleGate roles={["admin"]}>
      <PageHeader title="Population overview" description="Aggregates only. Admins cannot open individual patient records." />
      <OverviewDashboard />
    </RoleGate>
  );
}
