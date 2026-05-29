import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "danger" | "muted" | "warning";

const styles: Record<Variant, string> = {
  default: "bg-zinc-800 text-zinc-100",
  success: "bg-emerald-700/30 text-emerald-300 border border-emerald-700/50",
  danger:  "bg-rose-700/30 text-rose-300 border border-rose-700/50",
  warning: "bg-amber-700/30 text-amber-300 border border-amber-700/50",
  muted:   "bg-zinc-800/60 text-zinc-400 border border-zinc-700/50",
};

export const Badge: React.FC<React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }> = ({
  className, variant = "default", ...props
}) => (
  <span className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
    styles[variant], className)} {...props} />
);
