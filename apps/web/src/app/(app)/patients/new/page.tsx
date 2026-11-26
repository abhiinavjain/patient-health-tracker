import type { Metadata } from "next";
import { NewPatient } from "./new-patient";

export const metadata: Metadata = { title: "Register patient" };
export default function Page() {
  return <NewPatient />;
}
