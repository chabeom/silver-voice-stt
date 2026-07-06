from __future__ import annotations

from pathlib import Path

from stt_inference.audio import apply_energy_vad, convert_to_mono_16k, ensure_parent, reduce_noise_if_enabled
from stt_inference.confidence import ConfidenceCalibrator, average_confidence
from stt_inference.config import InferenceSettings
from stt_inference.diarization import assign_speakers_to_segments, run_speaker_diarization
from stt_inference.engine import WhisperEngine
from stt_inference.postprocess import normalize_korean_text
from stt_inference.remote_api import is_remote_backend, transcribe_with_remote_api
from stt_inference.schemas import InferenceResult, SegmentResult


def run_stt_pipeline(
    *,
    input_path: str,
    settings: InferenceSettings,
    enable_noise_reduction: bool,
    enable_speaker_diarization: bool = False,
    expected_speakers: int | None = None,
    job_id: str,
    display_name: str | None = None,
) -> InferenceResult:
    working_dir = Path(input_path).resolve().parent
    mono_path = str(working_dir / f"{job_id}_mono.wav")
    vad_path = str(working_dir / f"{job_id}_vad.wav")
    denoise_path = str(working_dir / f"{job_id}_denoise.wav")

    ensure_parent(mono_path)
    converted_path = convert_to_mono_16k(input_path, mono_path)

    if is_remote_backend(settings.model_backend):
        # The NAS inference API performs its own chunking, so keep the original
        # converted timeline instead of concatenating VAD frames locally.
        processed_path = reduce_noise_if_enabled(converted_path, denoise_path, enable_noise_reduction)
        raw = transcribe_with_remote_api(
            input_path=processed_path,
            settings=settings,
            display_name=display_name,
        )
    else:
        # Diarization relies on the original timeline, so do not concatenate
        # voiced frames when speaker assignment is requested.
        voiced_path = (
            converted_path
            if enable_speaker_diarization
            else apply_energy_vad(converted_path, vad_path)
        )
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
    calibrator = ConfidenceCalibrator.from_file(settings.confidence_calibration_path)
    raw_segments = raw["segments"]
    raw_duration = max((float(segment["end_sec"]) for segment in raw_segments), default=0.0)
    speaker_turns = None
    if enable_speaker_diarization:
        speaker_turns = run_speaker_diarization(
            processed_path,
            model_name=settings.diarization_model,
            token=settings.diarization_hf_token,
            device=settings.diarization_device,
            num_speakers=expected_speakers,
            mock_mode=settings.mock_mode,
            duration=raw_duration,
        )
        raw_segments = assign_speakers_to_segments(raw_segments, speaker_turns)

    segments: list[SegmentResult] = []
    raw_confidence_values: list[float] = []
    calibrated_confidence_values: list[float] = []
    for segment in raw_segments:
        normalized_text = normalize_korean_text(segment["text"])
        raw_confidence = float(segment.get("raw_confidence", segment["confidence"]))
        calibrated_confidence = calibrator.calibrate(raw_confidence)
        raw_confidence_values.append(raw_confidence)
        calibrated_confidence_values.append(calibrated_confidence)
        segments.append(
            SegmentResult(
                segment_index=segment["segment_index"],
                start_sec=float(segment["start_sec"]),
                end_sec=float(segment["end_sec"]),
                text=segment["text"],
                normalized_text=normalized_text,
                confidence=calibrated_confidence,
                raw_confidence=raw_confidence,
                calibrated_confidence=calibrated_confidence,
                speaker_label=segment.get("speaker_label"),
                speaker_display_name=segment.get("speaker_display_name"),
                speaker_confidence=segment.get("speaker_confidence"),
                avg_logprob=segment.get("avg_logprob"),
                no_speech_prob=segment.get("no_speech_prob"),
                tokens_json=segment.get("tokens_json"),
                is_low_confidence=calibrated_confidence < settings.low_confidence_threshold,
            )
        )

    normalized_full_text = " ".join(segment.normalized_text for segment in segments).strip()
    duration = max((segment.end_sec for segment in segments), default=0.0)
    low_conf_count = len([segment for segment in segments if segment.is_low_confidence])

    return InferenceResult(
        language=raw.get("language", "ko"),
        full_text=" ".join(segment.text for segment in segments).strip(),
        normalized_text=normalized_full_text,
        average_confidence=average_confidence(calibrated_confidence_values),
        average_raw_confidence=average_confidence(raw_confidence_values),
        average_calibrated_confidence=average_confidence(calibrated_confidence_values),
        calibration_applied=calibrator.is_calibrated,
        diarization_applied=bool(speaker_turns),
        speaker_count=len({str(turn["speaker_label"]) for turn in (speaker_turns or [])}),
        speaker_turns=speaker_turns,
        low_confidence_ratio=(low_conf_count / len(segments)) if segments else 0.0,
        duration=duration,
        segments=segments,
        processed_audio_path=processed_path,
    )
