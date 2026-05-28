"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import type { Job } from "@silver-voice/shared-types";
import { Button, Card, CardContent, CardHeader, CardTitle, Progress } from "@silver-voice/ui";

import { getAccessToken } from "@/lib/auth";
import { deleteJob, fetchJobs, getErrorMessage } from "@/lib/api";
import { getStatusLabel } from "@/lib/status";

import { FeedbackPopup } from "./feedback-popup";
import { StatusBadge } from "./status-badge";

const ACTIVE_STATUSES = new Set(["queued", "preprocessing", "running", "postprocessing"]);

export function JobsList() {
  const token = useMemo(() => getAccessToken(), []);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [errorPopup, setErrorPopup] = useState("");
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    fetchJobs(token)
      .then((data) => setJobs(data.items))
      .catch((err) => setErrorPopup(getErrorMessage(err, "작업 목록을 불러오지 못했습니다.")));
  }, [token]);

  const handleDelete = async (job: Job) => {
    if (!token || ACTIVE_STATUSES.has(job.status)) return;

    const confirmed = window.confirm(`"${job.original_filename}" 작업을 삭제할까요? 전사 결과와 정정 이력도 함께 삭제됩니다.`);
    if (!confirmed) return;

    setDeletingJobId(job.id);
    try {
      await deleteJob(token, job.id);
      setJobs((currentJobs) => currentJobs.filter((item) => item.id !== job.id));
    } catch (err) {
      setErrorPopup(getErrorMessage(err, "작업 삭제에 실패했습니다."));
    } finally {
      setDeletingJobId(null);
    }
  };

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
          const isDeleting = deletingJobId === job.id;
          const isActive = ACTIVE_STATUSES.has(job.status);

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

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <Link href={`/jobs/${job.id}`} className="inline-flex font-semibold text-sky-700">
                    상세 보기
                  </Link>
                  <Button
                    type="button"
                    variant="ghost"
                    className="min-h-10 rounded-2xl border-red-200/70 bg-red-50/80 px-4 text-sm text-red-700 hover:shadow-[0_14px_24px_rgba(185,28,28,0.12)]"
                    disabled={isActive || isDeleting}
                    title={isActive ? "처리 중인 작업은 완료되거나 실패한 뒤 삭제할 수 있습니다." : "작업 삭제"}
                    onClick={() => void handleDelete(job)}
                  >
                    {isDeleting ? "삭제 중..." : "삭제"}
                  </Button>
                </div>
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
