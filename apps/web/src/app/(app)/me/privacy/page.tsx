import type { Metadata } from "next";
import { Privacy } from "./privacy";

export const metadata: Metadata = { title: "Privacy & access" };
export default function Page() {
  return <Privacy />;
}
