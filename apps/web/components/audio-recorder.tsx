"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@silver-voice/ui";

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainSeconds = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainSeconds).padStart(2, "0")}`;
}

export function AudioRecorder({ onReady }: { onReady: (file: File) => void }) {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const isSupported = useMemo(
    () => typeof window !== "undefined" && typeof navigator !== "undefined" && !!navigator.mediaDevices,
    [],
  );

  useEffect(() => {
    if (!isRecording) {
      setElapsedSeconds(0);
      return;
    }

    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 250);

    return () => window.clearInterval(timer);
  }, [isRecording]);

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;
    chunksRef.current = [];
    recorder.ondataavailable = (inputEvent) => chunksRef.current.push(inputEvent.data);
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const file = new File([blob], `recording-${Date.now()}.webm`, { type: "audio/webm" });
      onReady(file);
      stream.getTracks().forEach((track) => track.stop());
    };
    recorder.start();
    setElapsedSeconds(0);
    setIsRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="space-y-3">
        <p className="section-kicker">Microphone Capture</p>
        <CardTitle>브라우저 녹음</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center gap-5 rounded-[1.6rem] border border-slate-200/50 bg-white/60 px-5 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.88)]">
          <div className={`recorder-orb ${isRecording ? "is-recording" : "is-idle"}`} />
          <div className="space-y-2">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Recorder Status</p>
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-lg font-semibold text-slate-950">{isRecording ? "녹음 중" : "대기 중"}</p>
              <div
                className={`rounded-full px-3 py-1 text-sm font-semibold ${
                  isRecording ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                }`}
              >
                {isRecording ? "REC" : "READY"}
              </div>
              <div className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
                {formatElapsed(elapsedSeconds)}
              </div>
            </div>
            <p className="text-base leading-7 text-slate-700">
              버튼을 누르면 즉시 마이크 입력을 수집하고, 녹음을 마치면 자동으로 업로드 가능한 파일 형태로
              변환합니다.
            </p>
          </div>
        </div>

        {!isSupported ? (
          <div className="signal-banner px-5 py-5">
            <p className="text-base leading-7 text-rose-700">
              현재 브라우저는 마이크 녹음을 지원하지 않습니다. 파일 업로드로 진행해 주세요.
            </p>
          </div>
        ) : isRecording ? (
          <Button onClick={stopRecording} className="w-full text-lg">
            녹음 종료
          </Button>
        ) : (
          <Button onClick={() => void startRecording()} className="w-full text-lg">
            녹음 시작
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
