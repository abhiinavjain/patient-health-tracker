import type { Metadata } from "next";
import { Insights } from "./insights";

export const metadata: Metadata = { title: "Panel insights" };
export default function Page() {
  return <Insights />;
}
