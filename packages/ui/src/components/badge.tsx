import type { ReactNode } from "react";

import { cn } from "../lib";

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3.5 py-1.5 text-sm font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,0.72),0_10px_18px_rgba(15,23,42,0.08)] backdrop-blur-md",
        tone === "default" &&
          "border-slate-200/70 bg-[linear-gradient(135deg,rgba(255,255,255,0.86),rgba(226,232,240,0.72))] text-slate-800",
        tone === "success" &&
          "border-emerald-200/70 bg-[linear-gradient(135deg,rgba(236,253,245,0.92),rgba(167,243,208,0.72))] text-emerald-900",
        tone === "warning" &&
          "border-amber-200/70 bg-[linear-gradient(135deg,rgba(255,251,235,0.92),rgba(253,230,138,0.72))] text-amber-900",
        tone === "danger" &&
          "border-rose-200/70 bg-[linear-gradient(135deg,rgba(255,241,242,0.94),rgba(254,205,211,0.72))] text-rose-900",
      )}
    >
      {children}
    </span>
  );
}
