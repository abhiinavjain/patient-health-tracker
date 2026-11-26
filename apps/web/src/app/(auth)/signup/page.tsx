import { Suspense } from "react";
import type { Metadata } from "next";
import { SignupForm } from "./signup-form";

export const metadata: Metadata = { title: "Create account" };

export default function SignupPage() {
  // Suspense: the form reads today's date (max date of birth), which must be computed per visit, not at build.
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}
