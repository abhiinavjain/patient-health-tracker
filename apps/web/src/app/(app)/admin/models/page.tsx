import type { Metadata } from "next";
import { Models } from "./models";

export const metadata: Metadata = { title: "Models" };
export default function Page() {
  return <Models />;
}
