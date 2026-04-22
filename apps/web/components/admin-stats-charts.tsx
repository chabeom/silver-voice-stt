"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ModelComparisonRow, OverviewStats } from "@silver-voice/shared-types";
import { Card, CardContent, CardHeader, CardTitle } from "@silver-voice/ui";

export function AdminStatsCharts({
  overview,
  comparison,
}: {
  overview: OverviewStats;
  comparison: ModelComparisonRow[];
}) {
  const summaryCards = [
    { label: "전체 작업", value: overview.total_jobs },
    { label: "완료 작업", value: overview.completed_jobs },
    { label: "실패 작업", value: overview.failed_jobs },
    { label: "교정 건수", value: overview.correction_count },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        {summaryCards.map((item) => (
          <div key={item.label} className="metric-tile px-5 py-5">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">{item.label}</p>
            <p className="mt-3 text-3xl font-semibold text-slate-950">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>모델별 평균 신뢰도</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparison}>
                <CartesianGrid stroke="rgba(148,163,184,0.22)" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="version_name" tick={{ fill: "#334155", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#334155", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 18,
                    border: "1px solid rgba(148,163,184,0.22)",
                    background: "rgba(255,255,255,0.94)",
                    boxShadow: "0 20px 40px rgba(15,23,42,0.12)",
                  }}
                />
                <Bar dataKey="average_confidence" radius={[14, 14, 6, 6]}>
                  {comparison.map((_, index) => (
                    <Cell key={index} fill={index % 2 === 0 ? "#2563eb" : "#0f766e"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>모델별 처리 시간</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={comparison}>
                <CartesianGrid stroke="rgba(148,163,184,0.22)" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="version_name" tick={{ fill: "#334155", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#334155", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 18,
                    border: "1px solid rgba(148,163,184,0.22)",
                    background: "rgba(255,255,255,0.94)",
                    boxShadow: "0 20px 40px rgba(15,23,42,0.12)",
                  }}
                />
                <Line type="monotone" dataKey="average_processing_ms" stroke="#f97316" strokeWidth={4} dot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
