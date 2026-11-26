"use client";

import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api";

let browserClient: QueryClient | undefined;

function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 20_000,
        refetchOnWindowFocus: false,
        // Don't retry auth/permission/not-found errors — they won't fix themselves.
        retry: (count, err) => !(err instanceof ApiError && [401, 403, 404, 422].includes(err.status)) && count < 2,
      },
    },
  });
}

function getClient() {
  if (typeof window === "undefined") return makeClient();
  browserClient ??= makeClient();
  return browserClient;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={getClient()}>
        <TooltipProvider delayDuration={200}>
          {children}
          <Toaster richColors position="top-right" />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
