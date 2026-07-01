"use client";

import { useState } from "react";

import type { JobDetail } from "@silver-voice/shared-types";
import { Button, Card, CardContent, CardHeader, CardTitle, Progress, Textarea } from "@silver-voice/ui";

import { getErrorMessage, saveCorrection } from "@/lib/api";

import { ConfidenceHighlight } from "./confidence-highlight";
import { FeedbackPopup } from "./feedback-popup";
import { StatusBadge } from "./status-badge";

export function TranscriptEditor({ detail, token }: { detail: JobDetail; token: string }) {
  const [text, setText] = useState(detail.transcript?.normalized_text ?? "");
  const [savedMessage, setSavedMessage] = useState("");
  const [errorPopup, setErrorPopup] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const averageConfidence = (detail.transcript?.average_confidence ?? 0) * 100;

  async function handleSave() {
    setIsSaving(true);
    try {
      await saveCorrection(token, detail.id, text);
      setSavedMessage("수정 내용이 저장되었습니다.");
    } catch (error) {
      setErrorPopup(getErrorMessage(error, "저장 중 오류가 발생했습니다."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      <div className="space-y-6">
        <section className="page-hero">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <p className="section-kicker">Transcript Review</p>
              <h2 className="section-title text-[clamp(1.9rem,2.8vw,2.8rem)]">{detail.original_filename}</h2>
              <p className="section-copy">
                모델 결과를 검토하고 필요하면 직접 수정한 뒤 correction 데이터로 저장할 수 있습니다.
              </p>
            </div>
            <StatusBadge status={detail.status} />
          </div>
        </section>

        <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>오디오 지표</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {detail.audio_url ? <audio controls className="w-full" src={detail.audio_url} /> : null}

              <div className="metric-tile px-5 py-5">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Average Confidence</p>
                <p className="mt-3 text-3xl font-semibold text-slate-950">{averageConfidence.toFixed(1)}%</p>
              </div>

              <Progress value={averageConfidence} />

              <div className="glass-grid md:grid-cols-2">
                <div className="signal-banner px-4 py-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Duration</p>
                  <p className="mt-2 text-base font-semibold text-slate-900">
                    {(detail.transcript?.total_duration ?? 0).toFixed(2)}초
                  </p>
                </div>
                <div className="signal-banner px-4 py-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Processing Time</p>
                  <p className="mt-2 text-base font-semibold text-slate-900">
                    {detail.transcript?.processing_ms ?? 0} ms
                  </p>
                </div>
              </div>

              {detail.transcript?.diarization_applied ? (
                <div className="signal-banner px-4 py-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Speaker Diarization</p>
                  <p className="mt-2 text-base font-semibold text-sky-800">
                    화자 {detail.transcript.speaker_count ?? 0}명을 분리했습니다.
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="depth-card--glow overflow-hidden">
            <CardHeader>
              <CardTitle>Transcript Editor</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Textarea value={text} onChange={(inputEvent) => setText(inputEvent.target.value)} />
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={() => void handleSave()} disabled={isSaving} className="w-full md:w-auto">
                  {isSaving ? "저장 중..." : "수정 내용 저장"}
                </Button>
                {detail.latest_correction ? (
                  <div className="signal-banner px-4 py-3">
                    <p className="text-sm font-medium text-slate-700">
                      최근 수정본이 {new Date(detail.latest_correction.created_at).toLocaleString("ko-KR")} 에 저장되었습니다.
                    </p>
                  </div>
                ) : null}
              </div>
              {savedMessage ? <p className="text-base font-medium text-slate-700">{savedMessage}</p> : null}
            </CardContent>
          </Card>
        </div>

        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="section-kicker">Segment Confidence</p>
              <h3 className="section-title text-[clamp(1.7rem,2.2vw,2.2rem)]">문장별 신뢰도</h3>
            </div>
            <p className="text-base text-slate-600">{detail.transcript?.segments.length ?? 0}개 세그먼트</p>
          </div>
          <div className="glass-grid">
            {detail.transcript?.segments.map((segment) => (
              <ConfidenceHighlight key={segment.id} segment={segment} />
            ))}
          </div>
        </section>
      </div>

      <FeedbackPopup
        open={Boolean(errorPopup)}
        title="저장 실패"
        description={errorPopup}
        onClose={() => setErrorPopup("")}
      />
    </>
  );
}
