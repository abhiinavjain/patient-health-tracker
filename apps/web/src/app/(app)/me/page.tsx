import type { Metadata } from "next";
import { MyHealth } from "./my-health";

export const metadata: Metadata = { title: "My health" };
export default function Page() {
  return <MyHealth />;
}
