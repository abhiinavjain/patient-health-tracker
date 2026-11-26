import type { Metadata } from "next";
import { AdminHome } from "./admin-home";

export const metadata: Metadata = { title: "Population" };
export default function Page() {
  return <AdminHome />;
}
