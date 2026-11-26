"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Loader2, Stethoscope, User as UserIcon, BarChart3 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { authRequest } from "@/lib/api";
import type { User } from "@/lib/types";

const DEMO_PASSWORD = "demo-password-123"; // seeded demo accounts only (see apps/api/app/seed.py)
const DEMOS = [
  { email: "doctor1@demo.pht", label: "Clinician", hint: "Dr. Ritu Malhotra · Internal medicine", icon: Stethoscope },
  { email: "patient1@demo.pht", label: "Patient", hint: "Own record, consent & privacy", icon: UserIcon },
  { email: "admin@demo.pht", label: "Admin", hint: "Population analytics & models", icon: BarChart3 },
];

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  async function signIn(e: string, p: string) {
    setError(null);
    setPending(e);
    try {
      const user = await authRequest<User>("login", { email: e, password: p });
      qc.setQueryData(["me"], user);
      const next = params.get("next");
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
      setPending(null);
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-1.5">
        <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
        <p className="text-sm text-muted-foreground">Use your account, or try a demo role below.</p>
      </div>

      <form
        className="space-y-4"
        onSubmit={(ev) => {
          ev.preventDefault();
          signIn(email, password);
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="current-password" required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <Button type="submit" className="w-full" disabled={!!pending}>
          {pending === email && <Loader2 className="animate-spin" aria-hidden />}
          Sign in
        </Button>
      </form>

      <div className="space-y-3">
        <div className="flex items-center gap-3 text-xs uppercase tracking-wide text-muted-foreground">
          <span className="h-px flex-1 bg-border" /> Demo accounts <span className="h-px flex-1 bg-border" />
        </div>
        <div className="grid gap-2">
          {DEMOS.map(({ email: e, label, hint, icon: Icon }) => (
            <button
              key={e}
              type="button"
              onClick={() => signIn(e, DEMO_PASSWORD)}
              disabled={!!pending}
              className="flex items-center gap-3 rounded-lg border bg-card p-3 text-left transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-60"
            >
              <span className="grid size-9 place-items-center rounded-md bg-accent text-accent-foreground">
                {pending === e ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Icon className="size-4" aria-hidden />}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">Continue as {label}</span>
                <span className="block truncate text-xs text-muted-foreground">{hint}</span>
              </span>
            </button>
          ))}
        </div>
      </div>

      <p className="text-center text-sm text-muted-foreground">
        New patient?{" "}
        <Link href="/signup" className="font-medium text-primary underline-offset-4 hover:underline">
          Create your health record
        </Link>
      </p>
    </div>
  );
}
