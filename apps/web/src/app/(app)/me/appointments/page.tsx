import type { Metadata } from "next";
import { MyAppointments } from "./my-appointments";

export const metadata: Metadata = { title: "Appointments" };
export default function Page() {
  return <MyAppointments />;
}
