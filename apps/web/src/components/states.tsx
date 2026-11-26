"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, Inbox, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import type { Role } from "@/lib/types";

export function PageHeader({ title, description, actions }: { title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center">
      <Inbox className="size-6 text-muted-foreground" aria-hidden />
      <p className="text-sm font-medium">{title}</p>
      {text && <p className="max-w-sm text-sm text-muted-foreground">{text}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const status = error instanceof ApiError ? error.status : 0;
  const message = error instanceof Error ? error.message : "Something went wrong";
  return (
    <div role="alert" className="flex flex-col items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-10 text-center">
      {status === 403 ? <Lock className="size-6 text-destructive" aria-hidden /> : <AlertTriangle className="size-6 text-destructive" aria-hidden />}
      <p className="text-sm font-medium">{status === 403 ? "No access" : "Couldn’t load this"}</p>
      <p className="max-w-md text-sm text-muted-foreground">{message}</p>
      {retry && status !== 403 && <Button variant="outline" size="sm" onClick={retry}>Try again</Button>}
    </div>
  );
}

export function LoadingRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-12" />)}
    </div>
  );
}

/** Renders children only for the given roles; otherwise a friendly pointer home. */
export function RoleGate({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { data: me } = useMe();
  if (!me)
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40" />
      </div>
    );
  if (!roles.includes(me.role))
    return (
      <EmptyState
        title="This page isn’t available for your role"
        action={<Button asChild size="sm" variant="outline"><Link href="/">Go to your home page</Link></Button>}
      />
    );
  return <>{children}</>;
}
