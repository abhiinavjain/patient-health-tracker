import { Brand } from "@/components/brand";
import { Activity, LockKeyhole, ShieldCheck } from "lucide-react";

const POINTS = [
  { icon: Activity, title: "One longitudinal record", text: "Every visit, diagnosis, lab and prescription in one timeline." },
  { icon: ShieldCheck, title: "Patient-controlled access", text: "Doctors see a record only with consent, and every view is logged." },
  { icon: LockKeyhole, title: "Explainable risk scores", text: "Calibrated models that show which factors drive each prediction." },
];

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="grid min-h-svh lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-primary p-10 text-primary-foreground lg:flex">
        <Brand className="[&>span]:bg-primary-foreground [&>span]:text-primary" />
        <div className="max-w-md space-y-8">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Continuity of care, with the patient in control.
          </h1>
          <ul className="space-y-5">
            {POINTS.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-3">
                <Icon className="mt-0.5 size-5 shrink-0 opacity-90" aria-hidden />
                <div>
                  <p className="font-medium">{title}</p>
                  <p className="text-sm opacity-80">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs opacity-70">Demo system on synthetic data. Not a medical device.</p>
        <div aria-hidden className="pointer-events-none absolute -right-24 -bottom-24 size-96 rounded-full bg-primary-foreground/10" />
      </aside>
      <main className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-sm">
          <Brand className="mb-8 lg:hidden" />
          {children}
        </div>
      </main>
    </div>
  );
}
