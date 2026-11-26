import { Suspense } from "react";
import type { Metadata } from "next";
import { PageSkeleton } from "@/components/page-skeleton";
import { PatientChart } from "./patient-chart";

export const metadata: Metadata = { title: "Patient chart" };

export default function Page() {
  // The patient id is runtime URL data (useParams), so it streams in behind this boundary.
  return (
    <Suspense fallback={<PageSkeleton />}>
      <PatientChart />
    </Suspense>
  );
}
