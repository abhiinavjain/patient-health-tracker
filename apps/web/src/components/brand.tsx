import { HeartPulse } from "lucide-react";
import { cn } from "@/lib/utils";

export function Brand({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2 font-semibold tracking-tight", className)}>
      <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
        <HeartPulse className="size-4.5" aria-hidden />
      </span>
      Health Tracker
    </span>
  );
}
