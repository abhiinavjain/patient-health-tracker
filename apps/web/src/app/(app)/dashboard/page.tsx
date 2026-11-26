import type { Metadata } from "next";
import { Dashboard } from "./dashboard";

export const metadata: Metadata = { title: "Worklist" };
export default function Page() {
  return <Dashboard />;
}
