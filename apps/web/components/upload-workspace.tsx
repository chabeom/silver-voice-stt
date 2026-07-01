"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import type { Job, ModelVersion } from "@silver-voice/shared-types";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Progress } from "@silver-voice/ui";

import { useJobEvents } from "@/hooks/use-job-events";
import { clearTokens, getAccessToken } from "@/lib/auth";
import { createJob, fetchModels, getErrorMessage, isAuthError, uploadAudioWithProgress } from "@/lib/api";
import { getStatusLabel } from "@/lib/status";

import { AudioRecorder } from "./audio-recorder";
import { FeedbackPopup } from "./feedback-popup";
import { StatusBadge } from "./status-badge";

export function UploadWorkspace() {
  const router = useRouter();
  const [token, setToken] = useState(() => getAccessToken());
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedJob, setUploadedJob] = useState<Job | null>(null);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [enableSpeakerDiarization, setEnableSpeakerDiarization] = useState(false);
  const [expectedSpeakers, setExpectedSpeakers] = useState(2);
  const [message, setMessage] = useState("로그인 후 음성 파일을 업로드해 주세요.");
  const [errorPopup, setErrorPopup] = useState("");
  const [redirectAfterPopup, setRedirectAfterPopup] = useState(false);
  const event = useJobEvents(activeJob?.id ?? null, token);

  function openErrorPopup(nextMessage: string, shouldRedirect = false) {
    setErrorPopup(nextMessage);
    setRedirectAfterPopup(shouldRedirect);
  }

  function closeErrorPopup() {
    setErrorPopup("");
    if (redirectAfterPopup) {
      setRedirectAfterPopup(false);
      router.replace("/login");
    }
  }

  function handleAuthFailure() {
    clearTokens();
    setToken("");
    setUploadedJob(null);
    setActiveJob(null);
    setUploadProgress(0);
    setMessage("로그인이 필요합니다.");
    openErrorPopup("로그인이 만료되었습니다. 다시 로그인해 주세요.", true);
  }

  useEffect(() => {
    const nextToken = getAccessToken();
    setToken(nextToken);

    if (!nextToken) {
      setMessage("로그인이 필요합니다.");
      router.replace("/login");
      return;
    }

    let ignore = false;

    async function loadModelsOnMount() {
      try {
        const response = await fetchModels(nextToken);
        if (ignore) return;
        setModels(response);
        setSelectedModel(response.find((model) => model.is_active)?.id ?? response[0]?.id ?? "");
      } catch (error) {
        if (ignore) return;
        if (isAuthError(error)) {
          handleAuthFailure();
          return;
        }
        openErrorPopup(getErrorMessage(error, "모델 목록을 불러오지 못했습니다."));
      }
    }

    void loadModelsOnMount();

    return () => {
      ignore = true;
    };
  }, [router]);

  async function handleUpload(file: File, uploadSource: "file" | "microphone") {
    const currentToken = getAccessToken();
    if (!currentToken) {
      handleAuthFailure();
      return;
    }

    setMessage("음성 파일을 업로드하고 있습니다.");
    setUploadProgress(0);

    try {
      const job = await uploadAudioWithProgress({
        file,
        token: currentToken,
        uploadSource,
        metadata: { device: navigator.userAgent },
        onProgress: setUploadProgress,
      });

      setUploadedJob(job);
      setActiveJob(null);
      setMessage("업로드가 완료되었습니다. 모델을 선택하고 STT를 실행해 주세요.");
    } catch (error) {
      if (isAuthError(error)) {
        handleAuthFailure();
        return;
      }
      setUploadProgress(0);
      openErrorPopup(getErrorMessage(error, "음성 업로드에 실패했습니다."));
    }
  }

  async function handleStartJob() {
    const currentToken = getAccessToken();
    if (!uploadedJob || !currentToken) {
      handleAuthFailure();
      return;
    }

    try {
      const job = await createJob(currentToken, uploadedJob.id, selectedModel, {
        enableSpeakerDiarization,
        expectedSpeakers,
      });
      setToken(currentToken);
      setActiveJob(job);
      setMessage("STT 작업을 시작했습니다.");
    } catch (error) {
      if (isAuthError(error)) {
        handleAuthFailure();
        return;
      }
      openErrorPopup(getErrorMessage(error, "STT 작업 시작에 실패했습니다."));
    }
  }

  const currentStatus = event?.status ?? activeJob?.status ?? uploadedJob?.status ?? "uploaded";
  const currentProgress = (event?.progress ?? activeJob?.progress ?? 0) * 100;

  return (
    <>
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="depth-card--glow overflow-hidden">
          <CardHeader className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="section-kicker">Input Console</p>
                <CardTitle className="mt-3">업로드 스테이션</CardTitle>
              </div>
              {uploadedJob ? <StatusBadge status={currentStatus} /> : null}
            </div>
            <div className="aurora-divider" />
          </CardHeader>

          <CardContent className="space-y-6">
            <div className="signal-banner space-y-3 px-5 py-5">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Current Message</p>
              <p className="text-lg font-medium leading-8 text-slate-900">{message}</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="metric-tile px-5 py-4">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Selected File</p>
                <p className="mt-3 text-base font-semibold text-slate-900">
                  {selectedFile?.name ?? uploadedJob?.original_filename ?? "아직 선택한 파일이 없습니다."}
                </p>
              </div>
              <div className="metric-tile px-5 py-4">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Available Models</p>
                <p className="mt-3 text-base font-semibold text-slate-900">{models.length || 0}개 모델 사용 가능</p>
              </div>
            </div>

            <div className="space-y-4">
              <Input
                type="file"
                accept="audio/*"
                onChange={(inputEvent) => setSelectedFile(inputEvent.target.files?.[0] ?? null)}
              />
              <Button
                className="w-full text-lg"
                onClick={() => selectedFile && void handleUpload(selectedFile, "file")}
                disabled={!selectedFile}
              >
                파일 업로드
              </Button>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3 text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                <span>Upload Progress</span>
                <span>{uploadProgress.toFixed(0)}%</span>
              </div>
              <Progress value={uploadProgress} />
            </div>

            {uploadedJob ? (
              <div className="signal-banner space-y-4 px-5 py-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Ready to Process</p>
                    <p className="mt-2 text-lg font-semibold text-slate-950">{uploadedJob.original_filename}</p>
                  </div>
                  <StatusBadge status={currentStatus} />
                </div>

                <select
                  className="surface-select"
                  value={selectedModel}
                  onChange={(selectEvent) => setSelectedModel(selectEvent.target.value)}
                >
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.version_name}
                    </option>
                  ))}
                </select>

                <div className="rounded-2xl border border-sky-200/70 bg-white/70 p-4">
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      checked={enableSpeakerDiarization}
                      onChange={(event) => setEnableSpeakerDiarization(event.target.checked)}
                      className="mt-1 h-5 w-5 accent-sky-600"
                    />
                    <span>
                      <span className="block font-semibold text-slate-950">화자 분리 사용</span>
                      <span className="mt-1 block text-sm leading-6 text-slate-600">
                        인터뷰나 대화 음성을 화자별로 구분합니다. 1인 음성은 끄는 것이 더 빠릅니다.
                      </span>
                    </span>
                  </label>

                  {enableSpeakerDiarization ? (
                    <label className="mt-4 block text-sm font-semibold text-slate-700">
                      예상 화자 수
                      <select
                        className="surface-select mt-2"
                        value={expectedSpeakers}
                        onChange={(event) => setExpectedSpeakers(Number(event.target.value))}
                      >
                        {[2, 3, 4, 5].map((count) => (
                          <option key={count} value={count}>
                            {count}명
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </div>

                <Button onClick={() => void handleStartJob()} className="w-full text-lg">
                  {enableSpeakerDiarization ? "화자 분리 + STT 실행" : "STT 실행"}
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="glass-grid">
          <AudioRecorder onReady={(file) => void handleUpload(file, "microphone")} />

          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>실시간 상태 모니터</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="metric-tile px-5 py-4">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Job Status</p>
                <p className="mt-3 text-2xl font-semibold text-slate-950">{getStatusLabel(currentStatus)}</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                  <span>Inference Progress</span>
                  <span>{currentProgress.toFixed(0)}%</span>
                </div>
                <Progress value={currentProgress} />
              </div>

              {activeJob ? (
                <div className="signal-banner space-y-3 px-5 py-5">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Live Job</p>
                  <p className="text-base font-medium leading-7 text-slate-800">
                    현재 작업 ID는 <span className="font-semibold text-slate-950">{activeJob.id}</span> 입니다.
                  </p>
                  {event?.status === "completed" ? (
                    <Link href={`/jobs/${activeJob.id}`} className="inline-flex font-semibold text-sky-700">
                      결과 상세 보기
                    </Link>
                  ) : null}
                </div>
              ) : (
                <div className="signal-banner px-5 py-5">
                  <p className="text-base leading-7 text-slate-700">
                    업로드가 끝나면 오른쪽 패널에서 작업 진행률과 현재 상태를 실시간으로 확인할 수 있습니다.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <FeedbackPopup
        open={Boolean(errorPopup)}
        title="작업 처리 실패"
        description={errorPopup}
        onClose={closeErrorPopup}
      />
    </>
  );
}
