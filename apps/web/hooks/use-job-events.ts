"use client";

import { useEffect, useState } from "react";

import type { JobEvent } from "@silver-voice/shared-types";

import { fetchJob, subscribeToJobEvents } from "@/lib/api";

export function useJobEvents(jobId: string | null, token: string) {
  const [event, setEvent] = useState<JobEvent | null>(null);

  useEffect(() => {
    if (!jobId || !token) return;

    let isDisposed = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;
    const source = subscribeToJobEvents(jobId, token, (nextEvent) => {
      if (isDisposed) return;
      setEvent(nextEvent);
      if (nextEvent.status === "completed" || nextEvent.status === "failed") {
        source.close();
        if (intervalId) clearInterval(intervalId);
      }
    });

    const syncLatestJob = async () => {
      try {
        const job = await fetchJob(token, jobId);
        if (isDisposed) return;
        setEvent({
          job_id: job.id,
          status: job.status,
          progress: job.progress,
          average_confidence: job.average_confidence ?? undefined,
          error_message: job.error_message ?? undefined,
        });
        if (job.status === "completed" || job.status === "failed") {
          source.close();
          if (intervalId) clearInterval(intervalId);
        }
      } catch {
        // SSE remains active; polling is only a fallback for stale UI state.
      }
    };

    void syncLatestJob();
    intervalId = setInterval(() => {
      void syncLatestJob();
    }, 2000);

    return () => {
      isDisposed = true;
      source.close();
      if (intervalId) clearInterval(intervalId);
    };
  }, [jobId, token]);

  return event;
}
