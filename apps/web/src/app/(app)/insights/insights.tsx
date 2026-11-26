"use client";

import { OverviewDashboard } from "@/components/charts/overview";
import { PageHeader, RoleGate } from "@/components/states";

export function Insights() {
  return (
    <RoleGate roles={["clinician"]}>
      <PageHeader title="Panel insights" description="Aggregate view of the patients who have granted you access." />
      <OverviewDashboard />
    </RoleGate>
  );
}
