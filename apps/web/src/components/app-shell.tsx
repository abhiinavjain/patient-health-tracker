"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";
import { useTheme } from "next-themes";
import { useQueryClient } from "@tanstack/react-query";
import {
  Activity, BarChart3, CalendarDays, ClipboardList, Cpu, HeartPulse, LogOut, Menu, Moon, ScrollText, ShieldCheck,
  Sun, Users, UserRound,
} from "lucide-react";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { authRequest } from "@/lib/api";
import { initials, titleCase } from "@/lib/format";
import { useMe } from "@/lib/hooks";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";

type NavItem = { href: string; label: string; icon: typeof Activity; exact?: boolean };

const NAV: Record<Role, NavItem[]> = {
  clinician: [
    { href: "/dashboard", label: "Worklist", icon: ClipboardList },
    { href: "/patients", label: "Patients", icon: Users },
    { href: "/schedule", label: "Schedule", icon: CalendarDays },
    { href: "/insights", label: "Panel insights", icon: BarChart3 },
  ],
  patient: [
    { href: "/me", label: "My health", icon: HeartPulse, exact: true },
    { href: "/me/health-check", label: "Health check", icon: Activity },
    { href: "/me/appointments", label: "Appointments", icon: CalendarDays },
    { href: "/me/privacy", label: "Privacy & access", icon: ShieldCheck },
  ],
  admin: [
    { href: "/admin", label: "Population", icon: BarChart3, exact: true },
    { href: "/admin/models", label: "Models", icon: Cpu },
    { href: "/admin/users", label: "Users", icon: Users },
    { href: "/admin/audit", label: "Audit log", icon: ScrollText },
  ],
};

function NavLinks({ role, onNavigate }: { role: Role; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="grid gap-1">
      {NAV[role].map(({ href, label, icon: Icon, exact }) => {
        const active = exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            <Icon className="size-4" aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function UserMenu() {
  const { data: me } = useMe();
  const { resolvedTheme, setTheme } = useTheme();
  const router = useRouter();
  const qc = useQueryClient();
  if (!me) return <Skeleton className="size-9 rounded-full" />;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-auto gap-2 px-2 py-1.5" aria-label="Account menu">
          <Avatar className="size-8">
            <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">{initials(me.full_name)}</AvatarFallback>
          </Avatar>
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-medium leading-tight">{me.full_name}</span>
            <span className="block text-xs text-muted-foreground">{me.specialty ?? titleCase(me.role)}</span>
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <p className="text-sm font-medium">{me.full_name}</p>
          <p className="truncate text-xs text-muted-foreground">{me.email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>
          {resolvedTheme === "dark" ? <Sun aria-hidden /> : <Moon aria-hidden />}
          {resolvedTheme === "dark" ? "Light mode" : "Dark mode"}
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={async () => {
            await authRequest("logout");
            qc.clear();
            router.replace("/login");
            router.refresh();
          }}
        >
          <LogOut aria-hidden /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { data: me } = useMe();
  const [open, setOpen] = useState(false);
  return (
    <div className="flex min-h-svh">
      <aside className="sticky top-0 hidden h-svh w-60 shrink-0 flex-col border-r bg-sidebar px-3 py-4 md:flex">
        <Link href="/" className="mb-6 px-2"><Brand /></Link>
        {me ? <NavLinks role={me.role} /> : <div className="grid gap-2 px-1">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-8" />)}</div>}
        <p className="mt-auto px-2 text-[11px] leading-snug text-muted-foreground">
          Demo on synthetic data. Not a medical device.
        </p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b bg-background/85 px-4 backdrop-blur sm:px-6">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open navigation"><Menu /></Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-4">
              <SheetTitle className="mb-6"><Brand /></SheetTitle>
              {me && <NavLinks role={me.role} onNavigate={() => setOpen(false)} />}
            </SheetContent>
          </Sheet>
          <Link href="/" className="md:hidden"><Brand className="text-sm" /></Link>
          <div className="ml-auto flex items-center gap-2">
            {me?.role === "patient" && (
              <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
                <Link href="/me/privacy"><UserRound aria-hidden /> Who can see my record</Link>
              </Button>
            )}
            <UserMenu />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:py-8">
          {/* Always render the page segment (it shows its own skeleton until the session loads), so the
              route is part of the prerendered shell and instant navigation can be validated. */}
          {children}
        </main>
      </div>
    </div>
  );
}
