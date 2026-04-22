import * as React from "react";

import { cn } from "../lib";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-48 w-full rounded-[1.5rem] border border-slate-200/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(240,245,255,0.88))] px-5 py-4 text-base leading-7 text-slate-900 shadow-[inset_0_1px_0_rgba(255,255,255,0.92),0_16px_28px_rgba(15,23,42,0.08)] placeholder:text-slate-400 transition duration-200 focus:border-sky-400/60 focus:outline-none focus:ring-4 focus:ring-sky-200/50",
        className,
      )}
      {...props}
    />
  ),
);

Textarea.displayName = "Textarea";
