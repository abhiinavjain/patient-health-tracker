"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authRequest } from "@/lib/api";
import type { User } from "@/lib/types";

export function SignupForm() {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", date_of_birth: "", sex: "" });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const user = await authRequest<User>("signup", form);
      qc.setQueryData(["me"], user);
      router.replace("/me");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create account");
      setPending(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-1.5">
        <h2 className="text-2xl font-semibold tracking-tight">Create your health record</h2>
        <p className="text-sm text-muted-foreground">You decide which doctors can see it.</p>
      </div>
      <form className="space-y-4" onSubmit={submit}>
        <div className="space-y-2">
          <Label htmlFor="full_name">Full name</Label>
          <Input id="full_name" required autoComplete="name" value={form.full_name} onChange={set("full_name")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" required autoComplete="email" value={form.email} onChange={set("email")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" required minLength={10} autoComplete="new-password" value={form.password}
                 onChange={set("password")} aria-describedby="pw-hint" />
          <p id="pw-hint" className="text-xs text-muted-foreground">At least 10 characters.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label htmlFor="dob">Date of birth</Label>
            <Input id="dob" type="date" required max={new Date().toISOString().slice(0, 10)} value={form.date_of_birth}
                   onChange={set("date_of_birth")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="sex">Sex</Label>
            <Select value={form.sex} onValueChange={(v) => setForm({ ...form, sex: v })} required>
              <SelectTrigger id="sex" className="w-full"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="female">Female</SelectItem>
                <SelectItem value="male">Male</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        {error && (
          <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>
        )}
        <Button type="submit" className="w-full" disabled={pending || !form.sex}>
          {pending && <Loader2 className="animate-spin" aria-hidden />} Create account
        </Button>
      </form>
      <p className="text-center text-sm text-muted-foreground">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">Sign in</Link>
      </p>
    </div>
  );
}
