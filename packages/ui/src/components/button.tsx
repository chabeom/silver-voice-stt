import * as React from "react";

import { cn } from "../lib";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "relative inline-flex min-h-12 items-center justify-center overflow-hidden rounded-[1.4rem] border px-5 text-base font-semibold tracking-[0.01em] transition duration-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-300/60 disabled:cursor-not-allowed disabled:opacity-50",
        "before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/80 before:content-['']",
        "after:absolute after:inset-0 after:bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.34)_24%,transparent_46%)] after:opacity-70 after:transition-transform after:duration-500 after:content-['']",
        "hover:-translate-y-1 hover:shadow-[0_24px_40px_rgba(15,23,42,0.16)] hover:after:translate-x-full active:translate-y-0",
        variant === "primary" &&
          "border-sky-400/40 bg-[linear-gradient(135deg,#2563eb_0%,#0891b2_55%,#0f766e_100%)] text-white shadow-[0_18px_36px_rgba(14,116,144,0.28),inset_0_1px_0_rgba(255,255,255,0.22)]",
        variant === "secondary" &&
          "border-amber-300/40 bg-[linear-gradient(135deg,#fff7d6_0%,#fde68a_55%,#fdba74_100%)] text-slate-900 shadow-[0_18px_30px_rgba(217,119,6,0.18),inset_0_1px_0_rgba(255,255,255,0.65)]",
        variant === "ghost" &&
          "border-slate-200/60 bg-white/70 text-slate-900 shadow-[0_14px_24px_rgba(15,23,42,0.08),inset_0_1px_0_rgba(255,255,255,0.88)] backdrop-blur-xl",
        className,
      )}
      {...props}
    />
  ),
);

Button.displayName = "Button";
