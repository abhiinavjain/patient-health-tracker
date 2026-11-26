import type { Metadata } from "next";
import { PatientList } from "./patient-list";

export const metadata: Metadata = { title: "Patients" };
export default function Page() {
  return <PatientList />;
}
