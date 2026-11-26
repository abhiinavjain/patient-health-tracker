import type { Metadata } from "next";
import { HealthCheck } from "./health-check";

export const metadata: Metadata = { title: "Health check" };
export default function Page() {
  return <HealthCheck />;
}
