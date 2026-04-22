import { Badge } from "@silver-voice/ui";
import type { JobStatus } from "@silver-voice/shared-types";

import { getStatusLabel } from "@/lib/status";

export function StatusBadge({ status }: { status: JobStatus | "missing" }) {
  if (status === "completed") return <Badge tone="success">{getStatusLabel(status)}</Badge>;
  if (status === "failed" || status === "missing") return <Badge tone="danger">{getStatusLabel(status)}</Badge>;
  if (status === "running" || status === "postprocessing" || status === "preprocessing") {
    return <Badge tone="warning">{getStatusLabel(status)}</Badge>;
  }
  return <Badge tone="default">{getStatusLabel(status)}</Badge>;
}

