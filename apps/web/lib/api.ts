import type {
  Job,
  JobDetail,
  JobEvent,
  ModelComparisonRow,
  ModelVersion,
  OverviewStats,
  PaginatedJobs,
} from "@silver-voice/shared-types";

import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, message: string, body = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function translateBackendMessage(message: string) {
  const normalized = message.trim();
  if (!normalized) return normalized;

  const lower = normalized.toLowerCase();

  if (lower.includes("invalid credentials")) {
    return "이메일 또는 비밀번호가 올바르지 않습니다.";
  }

  if (lower.includes("email already exists")) {
    return "이미 가입된 이메일입니다.";
  }

  if (lower.includes("invalid token")) {
    return "로그인 정보가 유효하지 않습니다. 다시 로그인해 주세요.";
  }

  if (lower.includes("user not found")) {
    return "사용자를 찾을 수 없습니다.";
  }

  if (lower.includes("job not found")) {
    return "작업 정보를 찾을 수 없습니다.";
  }

  if (lower.includes("audio upload not found")) {
    return "업로드한 음성 파일을 찾을 수 없습니다.";
  }

  if (lower.includes("transcript not ready")) {
    return "아직 음성 인식 결과가 준비되지 않았습니다.";
  }

  if (lower.includes("job already queued or completed")) {
    return "이미 처리 중이거나 완료된 작업입니다.";
  }

  if (lower.includes("active jobs cannot be deleted")) {
    return "처리 중인 작업은 완료되거나 실패한 뒤 삭제해 주세요.";
  }

  if (lower.includes("field required")) {
    return "필수 입력 항목이 비어 있습니다.";
  }

  if (lower.includes("value is not a valid email address")) {
    if (lower.includes("@-sign")) {
      return "이메일 형식이 올바르지 않습니다. @를 포함해 주세요.";
    }
    return "이메일 형식이 올바르지 않습니다.";
  }

  if (lower.includes("string should have at least 8 characters")) {
    return "비밀번호는 8자 이상 입력해 주세요.";
  }

  if (lower.includes("string should have at least 2 characters")) {
    return "이름은 2자 이상 입력해 주세요.";
  }

  if (lower.includes("string should have at most 128 characters")) {
    return "입력 길이가 너무 깁니다. 128자 이하로 입력해 주세요.";
  }

  if (lower.includes("string should have at most 120 characters")) {
    return "이름은 120자 이하로 입력해 주세요.";
  }

  if (lower.includes("network error")) {
    return "네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  }

  return normalized;
}

function extractErrorMessage(body: string, fallback: string) {
  if (!body) return fallback;

  try {
    const parsed = JSON.parse(body) as { detail?: string | { msg?: string }[] };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return translateBackendMessage(parsed.detail);
    }
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      const first = parsed.detail[0];
      if (first && typeof first.msg === "string" && first.msg.trim()) {
        return translateBackendMessage(first.msg);
      }
    }
  } catch {
    // Fall through to plain text handling.
  }

  return translateBackendMessage(body.trim() || fallback);
}

function createApiError(status: number, body: string, fallback: string) {
  return new ApiError(status, extractErrorMessage(body, fallback), body);
}

export function isAuthError(error: unknown) {
  return error instanceof ApiError && error.status === 401;
}

export function getErrorMessage(error: unknown, fallback = "요청 처리 중 오류가 발생했습니다.") {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message.trim()) return translateBackendMessage(error.message);
  return fallback;
}

async function apiFetch<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();
    throw createApiError(response.status, body, "API 요청에 실패했습니다.");
  }

  return response.json() as Promise<T>;
}

export function uploadAudioWithProgress({
  file,
  token,
  uploadSource,
  metadata,
  onProgress,
}: {
  file: File;
  token: string;
  uploadSource: "file" | "microphone";
  metadata: Record<string, unknown>;
  onProgress?: (value: number) => void;
}) {
  return new Promise<Job>((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("upload_source", uploadSource);
    formData.append("metadata_json", JSON.stringify(metadata));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/uploads/audio`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress?.((event.loaded / event.total) * 100);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as Job);
        return;
      }

      reject(createApiError(xhr.status, xhr.responseText, "음성 업로드에 실패했습니다."));
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}

export function register(payload: { email: string; full_name: string; password: string }) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: { email: string; password: string }) {
  return apiFetch<{ access_token: string; refresh_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchModels(token: string) {
  return apiFetch<ModelVersion[]>("/models", {}, token);
}

export function createJob(
  token: string,
  audioJobId: string,
  modelVersionId?: string,
  options: {
    enableSpeakerDiarization?: boolean;
    expectedSpeakers?: number | null;
  } = {},
) {
  return apiFetch<Job>(
    "/jobs",
    {
      method: "POST",
      body: JSON.stringify({
        audio_job_id: audioJobId,
        model_version_id: modelVersionId ?? null,
        enable_noise_reduction: false,
        enable_speaker_diarization: options.enableSpeakerDiarization ?? false,
        expected_speakers: options.enableSpeakerDiarization ? (options.expectedSpeakers ?? null) : null,
      }),
    },
    token,
  );
}

export function fetchJob(token: string, jobId: string) {
  return apiFetch<Job>(`/jobs/${jobId}`, {}, token);
}

export function fetchJobs(token: string) {
  return apiFetch<PaginatedJobs>("/jobs", {}, token);
}

export async function deleteJob(token: string, jobId: string) {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw createApiError(response.status, body, "작업 삭제에 실패했습니다.");
  }
}

export function fetchJobResult(token: string, jobId: string) {
  return apiFetch<JobDetail>(`/jobs/${jobId}/result`, {}, token);
}

export function fetchAdminJobDetail(token: string, jobId: string) {
  return apiFetch<JobDetail>(`/admin/jobs/${jobId}`, {}, token);
}

export function saveCorrection(token: string, jobId: string, correctedText: string) {
  return apiFetch(
    `/jobs/${jobId}/result`,
    {
      method: "PUT",
      body: JSON.stringify({
        corrected_text: correctedText,
        environment_metadata: {
          source: "web-editor",
        },
      }),
    },
    token,
  );
}

export function fetchAdminOverview(token: string) {
  return apiFetch<OverviewStats>("/admin/stats/overview", {}, token);
}

export function fetchModelComparison(token: string) {
  return apiFetch<ModelComparisonRow[]>("/admin/stats/model-comparison", {}, token);
}

export function fetchAdminJobs(token: string) {
  return apiFetch<Job[]>("/admin/jobs", {}, token);
}

export async function downloadCorrectionsExport(token: string) {
  const response = await fetch(`${API_BASE_URL}/admin/export/corrections`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw createApiError(response.status, body, "정정 데이터 내보내기에 실패했습니다.");
  }

  return response.blob();
}

export function subscribeToJobEvents(jobId: string, token: string, onEvent: (event: JobEvent) => void) {
  const url = new URL(`${API_BASE_URL}/jobs/${jobId}/events`);
  url.searchParams.set("access_token", token);
  const eventSource = new EventSource(url.toString(), { withCredentials: false });
  eventSource.onmessage = (event) => {
    onEvent(JSON.parse(event.data) as JobEvent);
  };
  eventSource.onerror = () => {};
  return eventSource;
}
