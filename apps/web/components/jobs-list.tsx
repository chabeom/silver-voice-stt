"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import type { Job } from "@silver-voice/shared-types";
import { Card, CardContent, CardHeader, CardTitle, Progress } from "@silver-voice/ui";

import { getAccessToken } from "@/lib/auth";
import { fetchJobs, getErrorMessage } from "@/lib/api";
import { getStatusLabel } from "@/lib/status";

import { FeedbackPopup } from "./feedback-popup";
import { StatusBadge } from "./status-badge";

export function JobsList() {
  const token = useMemo(() => getAccessToken(), []);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [errorPopup, setErrorPopup] = useState("");

  useEffect(() => {
    if (!token) return;
    fetchJobs(token)
      .then((data) => setJobs(data.items))
      .catch((err) => setErrorPopup(getErrorMessage(err, "작업 목록을 불러오지 못했습니다.")));
  }, [token]);

  if (!token) {
    return (
      <div className="signal-banner px-5 py-5">
        <p className="text-base leading-7 text-slate-700">작업 목록을 보려면 먼저 로그인해 주세요.</p>
      </div>
    );
  }

  return (
    <>
      <div className="glass-grid">
        {jobs.length === 0 ? (
          <Card>
            <CardContent className="py-10">
              <p className="text-lg font-medium text-slate-700">아직 업로드한 작업이 없습니다.</p>
            </CardContent>
          </Card>
        ) : null}

        {jobs.map((job) => {
          const progress = job.progress * 100;

          return (
            <Card key={job.id} className="overflow-hidden">
              <CardHeader className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                  <p className="section-kicker">Job Card</p>
                  <CardTitle>{job.original_filename}</CardTitle>
                  <p className="text-base text-slate-700">
                    입력 방식: {job.upload_source === "microphone" ? "마이크 녹음" : "파일 업로드"}
                  </p>
                </div>
                <StatusBadge status={job.status} />
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="glass-grid md:grid-cols-3">
                  <div className="metric-tile px-4 py-4">
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Confidence</p>
                    <p className="mt-2 text-lg font-semibold text-slate-950">
                      {((job.average_confidence ?? 0) * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="metric-tile px-4 py-4">
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Status</p>
                    <p className="mt-2 text-lg font-semibold text-slate-950">{getStatusLabel(job.status)}</p>
                  </div>
                  <div className="metric-tile px-4 py-4">
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Updated</p>
                    <p className="mt-2 text-lg font-semibold text-slate-950">
                      {new Date(job.updated_at).toLocaleDateString("ko-KR")}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-3 text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                    <span>Progress</span>
                    <span>{progress.toFixed(0)}%</span>
                  </div>
                  <Progress value={progress} />
                </div>

                <Link href={`/jobs/${job.id}`} className="inline-flex font-semibold text-sky-700">
                  상세 보기
                </Link>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <FeedbackPopup
        open={Boolean(errorPopup)}
        title="목록 로드 실패"
        description={errorPopup}
        onClose={() => setErrorPopup("")}
      />
    </>
  );
}
