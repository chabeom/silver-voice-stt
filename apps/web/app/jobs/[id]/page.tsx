"use client";

import { useEffect, useMemo, useState } from "react";

import type { JobDetail } from "@silver-voice/shared-types";

import { TranscriptEditor } from "@/components/transcript-editor";
import { getAccessToken } from "@/lib/auth";
import { fetchJobResult } from "@/lib/api";

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const token = useMemo(() => getAccessToken(), []);
  const [detail, setDetail] = useState<JobDetail | null>(null);

  useEffect(() => {
    if (!token) return;
    fetchJobResult(token, params.id).then(setDetail).catch(() => null);
  }, [params.id, token]);

  if (!detail) {
    return (
      <div className="page-hero">
        <p className="section-kicker">Transcript Detail</p>
        <h2 className="section-title mt-3">결과를 불러오는 중입니다</h2>
        <p className="section-copy mt-3">
          음성 파일과 세그먼트 결과를 3D 리뷰 화면에 맞춰 정리하고 있습니다.
        </p>
      </div>
    );
  }

  return <TranscriptEditor detail={detail} token={token} />;
}
