from pathlib import Path

from stt_inference.audio import apply_energy_vad, convert_to_mono_16k, ensure_parent, reduce_noise_if_enabled
from stt_inference.confidence import average_confidence
from stt_inference.config import InferenceSettings
from stt_inference.engine import WhisperEngine
from stt_inference.postprocess import normalize_korean_text
from stt_inference.schemas import InferenceResult, SegmentResult


def run_stt_pipeline(
    *,
    input_path: str,
    settings: InferenceSettings,
    enable_noise_reduction: bool,
    job_id: str,
    display_name: str | None = None,
) -> InferenceResult:
    working_dir = Path(input_path).resolve().parent
    mono_path = str(working_dir / f"{job_id}_mono.wav")
    vad_path = str(working_dir / f"{job_id}_vad.wav")
    denoise_path = str(working_dir / f"{job_id}_denoise.wav")

    ensure_parent(mono_path)
    converted_path = convert_to_mono_16k(input_path, mono_path)
    voiced_path = apply_energy_vad(converted_path, vad_path)
    processed_path = reduce_noise_if_enabled(voiced_path, denoise_path, enable_noise_reduction)

    engine = WhisperEngine(
        model_path=settings.model_path,
        download_root=settings.download_root,
        device=settings.device,
        compute_type=settings.compute_type,
        beam_size=settings.beam_size,
        best_of=settings.best_of,
        mock_mode=settings.mock_mode,
    )
    raw = engine.transcribe(processed_path, display_name=display_name)

    segments: list[SegmentResult] = []
    confidence_values: list[float] = []
    for segment in raw["segments"]:
        normalized_text = normalize_korean_text(segment["text"])
        confidence = float(segment["confidence"])
        confidence_values.append(confidence)
        segments.append(
            SegmentResult(
                segment_index=segment["segment_index"],
                start_sec=float(segment["start_sec"]),
                end_sec=float(segment["end_sec"]),
                text=segment["text"],
                normalized_text=normalized_text,
                confidence=confidence,
                avg_logprob=segment.get("avg_logprob"),
                no_speech_prob=segment.get("no_speech_prob"),
                tokens_json=segment.get("tokens_json"),
                is_low_confidence=confidence < settings.low_confidence_threshold,
            )
        )

    normalized_full_text = " ".join(segment.normalized_text for segment in segments).strip()
    duration = max((segment.end_sec for segment in segments), default=0.0)
    low_conf_count = len([segment for segment in segments if segment.is_low_confidence])

    return InferenceResult(
        language=raw.get("language", "ko"),
        full_text=" ".join(segment.text for segment in segments).strip(),
        normalized_text=normalized_full_text,
        average_confidence=average_confidence(confidence_values),
        low_confidence_ratio=(low_conf_count / len(segments)) if segments else 0.0,
        duration=duration,
        segments=segments,
        processed_audio_path=processed_path,
    )
