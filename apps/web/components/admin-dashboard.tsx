"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import type { Job, ModelComparisonRow, OverviewStats } from "@silver-voice/shared-types";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@silver-voice/ui";

import { getAccessToken } from "@/lib/auth";
import {
  downloadCorrectionsExport,
  fetchAdminJobs,
  fetchAdminOverview,
  fetchModelComparison,
  getErrorMessage,
} from "@/lib/api";

import { AdminStatsCharts } from "./admin-stats-charts";
import { FeedbackPopup } from "./feedback-popup";
import { StatusBadge } from "./status-badge";

export function AdminDashboard() {
  const token = useMemo(() => getAccessToken(), []);
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [comparison, setComparison] = useState<ModelComparisonRow[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [message, setMessage] = useState("");
  const [errorPopup, setErrorPopup] = useState("");
  const [showFailedOnly, setShowFailedOnly] = useState(false);

  useEffect(() => {
    if (!token) return;

    fetchAdminOverview(token).then(setOverview).catch((error) => setErrorPopup(getErrorMessage(error)));
    fetchModelComparison(token).then(setComparison).catch((error) => setErrorPopup(getErrorMessage(error)));
    fetchAdminJobs(token).then(setJobs).catch((error) => setErrorPopup(getErrorMessage(error)));
  }, [token]);

  if (!token) {
    return (
      <div className="signal-banner px-5 py-5">
        <p className="text-base leading-7 text-slate-700">관리자 화면은 로그인 후 이용할 수 있습니다.</p>
      </div>
    );
  }

  async function handleExport() {
    try {
      const blob = await downloadCorrectionsExport(token);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "corrections-export.csv";
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("교정 데이터 export를 시작했습니다.");
    } catch (error) {
      setErrorPopup(getErrorMessage(error, "교정 데이터 export에 실패했습니다."));
    }
  }

  const visibleJobs = showFailedOnly ? jobs.filter((job) => job.status === "failed") : jobs;

  return (
    <>
      <div className="space-y-6">
        {overview ? <AdminStatsCharts overview={overview} comparison={comparison} /> : null}

        <Card className="depth-card--glow overflow-hidden">
          <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <p className="section-kicker">Recent Activity</p>
              <CardTitle>최근 업로드 이력</CardTitle>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button variant={showFailedOnly ? "secondary" : "ghost"} onClick={() => setShowFailedOnly((prev) => !prev)}>
                실패 케이스만 보기
              </Button>
              <Button onClick={() => void handleExport()}>교정 데이터 export</Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {message ? (
              <div className="signal-banner px-5 py-4">
                <p className="text-base font-medium text-slate-700">{message}</p>
              </div>
            ) : null}

            {visibleJobs.slice(0, 8).map((job) => (
              <div
                key={job.id}
                className="signal-banner flex flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-2">
                  <p className="text-lg font-semibold text-slate-950">{job.original_filename}</p>
                  <p className="text-sm text-slate-600">
                    평균 신뢰도 {((job.average_confidence ?? 0) * 100).toFixed(1)}% ·{" "}
                    {new Date(job.updated_at).toLocaleString("ko-KR")}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={job.status} />
                  <Link href={`/admin/jobs/${job.id}`} className="font-semibold text-sky-700">
                    상세 분석
                  </Link>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <FeedbackPopup
        open={Boolean(errorPopup)}
        title="관리자 작업 실패"
        description={errorPopup}
        onClose={() => setErrorPopup("")}
      />
    </>
  );
}
