import type { JobStatus } from "@silver-voice/shared-types";

export type ExtendedJobStatus = JobStatus | "missing";

const STATUS_LABELS: Record<ExtendedJobStatus, string> = {
  uploaded: "\uC5C5\uB85C\uB4DC \uC644\uB8CC",
  queued: "\uB300\uAE30 \uC911",
  preprocessing: "\uC804\uCC98\uB9AC \uC911",
  running: "\uC74C\uC131 \uC778\uC2DD \uC911",
  postprocessing: "\uD6C4\uCC98\uB9AC \uC911",
  completed: "\uC644\uB8CC",
  failed: "\uC2E4\uD328",
  missing: "\uCC3E\uC744 \uC218 \uC5C6\uC74C",
};

export function getStatusLabel(status: ExtendedJobStatus) {
  return STATUS_LABELS[status] ?? status;
}
