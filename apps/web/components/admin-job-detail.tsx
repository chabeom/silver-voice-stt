"use client";

import { useEffect, useMemo, useState } from "react";

import type { JobDetail } from "@silver-voice/shared-types";
import { Card, CardContent, CardHeader, CardTitle } from "@silver-voice/ui";

import { getAccessToken } from "@/lib/auth";
import { fetchAdminJobDetail } from "@/lib/api";

import { ConfidenceHighlight } from "./confidence-highlight";
import { StatusBadge } from "./status-badge";

export function AdminJobDetail({ jobId }: { jobId: string }) {
  const token = useMemo(() => getAccessToken(), []);
  const [detail, setDetail] = useState<JobDetail | null>(null);

  useEffect(() => {
    if (!token) return;
    fetchAdminJobDetail(token, jobId).then(setDetail).catch(() => null);
  }, [jobId, token]);

  if (!detail) {
    return <p className="text-lg text-slate-700">상세 정보를 불러오는 중입니다.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="section-kicker">Job Snapshot</p>
          <h3 className="section-title mt-3 text-[clamp(1.7rem,2.3vw,2.3rem)]">{detail.original_filename}</h3>
        </div>
        <StatusBadge status={detail.status} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>예측문과 수정문 비교</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="signal-banner px-5 py-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Prediction</p>
              <p className="mt-3 text-lg leading-8 text-slate-900">{detail.transcript?.normalized_text ?? "예측 결과가 없습니다."}</p>
            </div>
            <div className="signal-banner bg-amber-50/80 px-5 py-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Correction</p>
              <p className="mt-3 text-lg leading-8 text-slate-900">
                {detail.latest_correction?.corrected_text ?? "아직 저장된 수정본이 없습니다."}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>원본 오디오와 지표</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {detail.audio_url ? <audio controls className="w-full" src={detail.audio_url} /> : null}

            <div className="glass-grid md:grid-cols-2">
              <div className="metric-tile px-4 py-4">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Average Confidence</p>
                <p className="mt-2 text-lg font-semibold text-slate-950">
                  {((detail.transcript?.average_confidence ?? 0) * 100).toFixed(1)}%
                </p>
              </div>
              <div className="metric-tile px-4 py-4">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Processing Time</p>
                <p className="mt-2 text-lg font-semibold text-slate-950">
                  {detail.transcript?.processing_ms ?? 0} ms
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <section className="space-y-4">
        <div>
          <p className="section-kicker">Segment Review</p>
          <h3 className="section-title mt-3 text-[clamp(1.7rem,2.2vw,2.2rem)]">문장별 confidence 분석</h3>
        </div>
        <div className="glass-grid">
          {detail.transcript?.segments.map((segment) => (
            <ConfidenceHighlight key={segment.id} segment={segment} />
          ))}
        </div>
      </section>
    </div>
  );
}
