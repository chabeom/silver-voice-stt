export type UserRole = "user" | "admin";
export type JobStatus =
  | "uploaded"
  | "queued"
  | "preprocessing"
  | "running"
  | "postprocessing"
  | "completed"
  | "failed";

export interface ModelVersion {
  id: string;
  version_name: string;
  model_family: string;
  locale: string;
  source_path: string;
  description: string;
  metrics_json?: Record<string, number | null> | null;
  is_active: boolean;
  created_at: string;
}

export interface TranscriptSegment {
  id: string;
  segment_index: number;
  start_sec: number;
  end_sec: number;
  text: string;
  normalized_text: string;
  confidence: number;
  raw_confidence?: number | null;
  calibrated_confidence?: number | null;
  speaker_label?: string | null;
  speaker_display_name?: string | null;
  speaker_confidence?: number | null;
  is_low_confidence: boolean;
  avg_logprob?: number | null;
  no_speech_prob?: number | null;
  tokens_json?: Array<Record<string, unknown>> | null;
}

export interface Transcript {
  id: string;
  job_id: string;
  language: string;
  full_text: string;
  normalized_text: string;
  average_confidence: number;
  average_raw_confidence?: number | null;
  average_calibrated_confidence?: number | null;
  calibration_applied?: boolean;
  diarization_applied?: boolean;
  speaker_count?: number;
  low_confidence_ratio: number;
  total_duration: number;
  processing_ms: number;
  segments: TranscriptSegment[];
}

export interface CorrectionSummary {
  id: string;
  corrected_text: string;
  created_at: string;
}

export interface Job {
  id: string;
  user_id: string;
  model_version_id?: string | null;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  upload_source: string;
  status: JobStatus;
  progress: number;
  average_confidence?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobDetail extends Job {
  transcript?: Transcript | null;
  latest_correction?: CorrectionSummary | null;
  audio_url?: string | null;
}

export interface PaginatedJobs {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface OverviewStats {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  correction_count: number;
  failure_rate: number;
  correction_rate: number;
  average_confidence: number;
  average_processing_ms: number;
}

export interface ModelComparisonRow {
  model_version_id?: string | null;
  version_name: string;
  completed_jobs: number;
  average_confidence: number;
  average_processing_ms: number;
  correction_rate: number;
}

export interface JobEvent {
  job_id: string;
  status: JobStatus | "missing";
  progress: number;
  average_confidence?: number | null;
  error_message?: string | null;
}
