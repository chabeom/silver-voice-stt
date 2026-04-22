import type { TranscriptSegment } from "@silver-voice/shared-types";

import { Badge, Card, CardContent, Progress } from "@silver-voice/ui";

export function ConfidenceHighlight({ segment }: { segment: TranscriptSegment }) {
  const confidencePercent = segment.confidence * 100;

  return (
    <Card className={segment.is_low_confidence ? "border-rose-300/60 bg-rose-50/80" : "border-slate-200/60"}>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Segment Window</p>
            <p className="mt-2 text-base font-semibold text-slate-900">
              {segment.start_sec.toFixed(2)}s - {segment.end_sec.toFixed(2)}s
            </p>
          </div>
          <Badge tone={segment.is_low_confidence ? "danger" : "success"}>신뢰도 {confidencePercent.toFixed(1)}%</Badge>
        </div>

        <Progress value={confidencePercent} />

        <div className="signal-banner px-5 py-5">
          <p className="text-lg leading-8 text-slate-900">{segment.normalized_text}</p>
        </div>

        {segment.is_low_confidence ? (
          <p className="text-sm font-medium text-rose-700">
            낮은 confidence 구간입니다. 원본 오디오와 함께 다시 확인해 주세요.
          </p>
        ) : (
          <p className="text-sm font-medium text-emerald-700">안정적으로 인식된 구간입니다.</p>
        )}
      </CardContent>
    </Card>
  );
}
