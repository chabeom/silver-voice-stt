import { cn } from "../lib";

export function Progress({ value, className }: { value: number; className?: string }) {
  const width = Math.max(0, Math.min(100, value));

  return (
    <div
      className={cn(
        "relative h-4 w-full overflow-hidden rounded-full border border-white/60 bg-[linear-gradient(180deg,rgba(226,232,240,0.72),rgba(203,213,225,0.64))] shadow-[inset_0_1px_0_rgba(255,255,255,0.82)]",
        className,
      )}
    >
      <div
        className="relative h-full rounded-full bg-[linear-gradient(90deg,#38bdf8_0%,#2563eb_45%,#0f766e_100%)] transition-all duration-500"
        style={{ width: `${width}%` }}
      >
        <span className="absolute inset-0 bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.42)_24%,transparent_46%)] animate-[sheen_4.8s_ease-in-out_infinite]" />
      </div>
    </div>
  );
}
