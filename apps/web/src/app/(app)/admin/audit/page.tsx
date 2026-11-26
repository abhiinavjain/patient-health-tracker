import type { Metadata } from "next";
import { Audit } from "./audit";

export const metadata: Metadata = { title: "Audit log" };
export default function Page() {
  return <Audit />;
}
