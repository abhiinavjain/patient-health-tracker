import { Suspense } from "react";
import type { Metadata } from "next";
import { PageSkeleton } from "@/components/page-skeleton";
import { Consult } from "./consult";

export const metadata: Metadata = { title: "New consultation" };

export default function Page() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Consult />
    </Suspense>
  );
}
