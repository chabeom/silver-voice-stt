"use client";

import { Button } from "@silver-voice/ui";

type FeedbackTone = "error" | "info";

const toneStyles: Record<FeedbackTone, { kicker: string; ring: string; panel: string }> = {
  error: {
    kicker: "System Alert",
    ring: "shadow-[0_30px_80px_rgba(127,29,29,0.22)]",
    panel: "bg-rose-50/88",
  },
  info: {
    kicker: "System Notice",
    ring: "shadow-[0_30px_80px_rgba(15,23,42,0.24)]",
    panel: "bg-white/75",
  },
};

export function FeedbackPopup({
  open,
  title,
  description,
  onClose,
  tone = "error",
  actionLabel = "확인",
}: {
  open: boolean;
  title: string;
  description: string;
  onClose: () => void;
  tone?: FeedbackTone;
  actionLabel?: string;
}) {
  if (!open) return null;

  const palette = toneStyles[tone];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 backdrop-blur-sm">
      <div className={`depth-card depth-card--glow w-full max-w-md rounded-[2rem] px-6 py-6 ${palette.ring}`}>
        <div className="space-y-4">
          <div className="space-y-2">
            <p className="section-kicker">{palette.kicker}</p>
            <h2 className="font-[Georgia,'Times_New_Roman',serif] text-3xl font-semibold tracking-[-0.02em] text-slate-950">
              {title}
            </h2>
          </div>
          <div className={`signal-banner px-5 py-5 ${palette.panel}`}>
            <p className="text-base leading-7 text-slate-800">{description}</p>
          </div>
          <Button onClick={onClose} className="w-full text-lg">
            {actionLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
