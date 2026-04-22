import * as React from "react";

import { cn } from "../lib";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "min-h-[3.35rem] w-full rounded-[1.3rem] border border-slate-200/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(240,245,255,0.88))] px-4 text-base text-slate-900 shadow-[inset_0_1px_0_rgba(255,255,255,0.92),0_12px_24px_rgba(15,23,42,0.08)] placeholder:text-slate-400 transition duration-200 focus:border-sky-400/60 focus:outline-none focus:ring-4 focus:ring-sky-200/50",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
