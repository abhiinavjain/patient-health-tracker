import type { Metadata } from "next";
import { Schedule } from "./schedule";

export const metadata: Metadata = { title: "Schedule" };
export default function Page() {
  return <Schedule />;
}
