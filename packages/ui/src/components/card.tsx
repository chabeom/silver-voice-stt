import * as React from "react";

import { cn } from "../lib";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("depth-card rounded-[2rem]", className)} {...props} />;
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("border-b border-slate-200/50 px-6 py-5 md:px-7", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn(
        "font-[Georgia,'Times_New_Roman',serif] text-[1.45rem] font-semibold tracking-[-0.02em] text-slate-950",
        className,
      )}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-6 py-5 md:px-7 md:py-6", className)} {...props} />;
}
