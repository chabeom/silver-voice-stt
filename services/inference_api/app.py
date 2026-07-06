from __future__ import annotations

import math
import os
import statistics
import tempfile
import time
from functools import lru_cache
from math import gcd
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware


DEFAULT_BASE_MODEL = "openai/whisper-medium"
DEFAULT_ADAPTER_PATH = "models/whisper-medium-forced-v1-trip"
DEFAULT_CHUNK_SECONDS = 30.0
DEFAULT_CHUNK_OVERLAP_SECONDS = 0.0
DEFAULT_MIN_CHUNK_RMS = 0.0005


app = FastAPI(title="Silver Voice STT Inference API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else Path.cwd() / path


def _normalize_text(text: str) -> str:
    return " ".join(str(text).strip().split())


def _read_audio(audio_path: Path) -> tuple[Any, int, float]:
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    audio, sampling_rate = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sampling_rate != 16000:
        common = gcd(sampling_rate, 16000)
        audio = resample_poly(audio, 16000 // common, sampling_rate // common).astype(np.float32)
        sampling_rate = 16000
    duration = float(len(audio) / sampling_rate) if sampling_rate else 0.0
    return audio, sampling_rate, duration


def _confidence_from_scores(model: Any, generated: Any) -> tuple[float, float]:
    transition_scores = model.compute_transition_scores(
        generated.sequences,
        generated.scores,
        normalize_logits=True,
    )
    token_scores = transition_scores[0].detach().float().cpu().tolist()
    finite_scores = [score for score in token_scores if math.isfinite(score)]
    avg_logprob = statistics.fmean(finite_scores) if finite_scores else float("-inf")
    raw_confidence = math.exp(min(0.0, avg_logprob)) if math.isfinite(avg_logprob) else 0.0
    return float(avg_logprob), float(raw_confidence)


def _iter_audio_chunks(
    audio: Any,
    *,
    sampling_rate: int,
    chunk_seconds: float,
    chunk_overlap_seconds: float,
    min_chunk_rms: float,
) -> list[dict[str, Any]]:
    import numpy as np

    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be greater than 0")
    if chunk_overlap_seconds < 0:
        raise ValueError("chunk_overlap_seconds must be 0 or greater")
    if chunk_overlap_seconds >= chunk_seconds:
        raise ValueError("chunk_overlap_seconds must be smaller than chunk_seconds")

    chunk_samples = max(1, int(chunk_seconds * sampling_rate))
    overlap_samples = max(0, int(chunk_overlap_seconds * sampling_rate))
    step_samples = max(1, chunk_samples - overlap_samples)
    total_samples = len(audio)
    chunks: list[dict[str, Any]] = []

    start = 0
    while start < total_samples:
        end = min(total_samples, start + chunk_samples)
        chunk_audio = audio[start:end]
        if len(chunk_audio) == 0:
            break

        rms = float(np.sqrt(np.mean(np.square(chunk_audio)))) if len(chunk_audio) else 0.0
        if rms >= min_chunk_rms:
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "start_sec": start / sampling_rate,
                    "end_sec": end / sampling_rate,
                    "audio": chunk_audio,
                    "rms": rms,
                }
            )

        if end >= total_samples:
            break
        start += step_samples

    return chunks


def _transcribe_audio_chunk(
    *,
    bundle: dict[str, Any],
    audio: Any,
    sampling_rate: int,
    language: str,
    task: str,
    max_new_tokens: int,
) -> tuple[str, float, float]:
    import torch

    processor = bundle["processor"]
    model = bundle["model"]
    device = bundle["device"]
    input_features = processor(
        audio,
        sampling_rate=sampling_rate,
        return_tensors="pt",
    ).input_features.to(device)

    with torch.inference_mode():
        generated = model.generate(
            input_features,
            language=language,
            task=task,
            max_new_tokens=max_new_tokens,
            return_dict_in_generate=True,
            output_scores=True,
        )
    text = _normalize_text(processor.tokenizer.decode(generated.sequences[0], skip_special_tokens=True))
    avg_logprob, raw_confidence = _confidence_from_scores(model, generated)
    return text, avg_logprob, raw_confidence


@lru_cache(maxsize=1)
def _load_model() -> dict[str, Any]:
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    base_model = os.getenv("STT_BASE_MODEL", DEFAULT_BASE_MODEL)
    adapter_path = os.getenv("STT_ADAPTER_PATH", DEFAULT_ADAPTER_PATH)
    device_name = os.getenv("STT_DEVICE", "cuda")
    local_files_only = _env_bool("STT_LOCAL_FILES_ONLY", False)

    adapter_resolved = _resolve_path(adapter_path)
    processor_source = str(adapter_resolved) if adapter_resolved.exists() else base_model
    processor = WhisperProcessor.from_pretrained(
        processor_source,
        local_files_only=local_files_only,
    )

    model = WhisperForConditionalGeneration.from_pretrained(
        base_model,
        local_files_only=local_files_only,
    )
    if adapter_path:
        if not adapter_resolved.exists():
            raise RuntimeError(f"Adapter path not found: {adapter_resolved}")
        from peft import PeftModel

        model = PeftModel.from_pretrained(
            model,
            str(adapter_resolved),
            local_files_only=local_files_only,
        )

    device = torch.device(device_name)
    model.to(device)
    model.eval()
    return {
        "base_model": base_model,
        "adapter_path": str(adapter_resolved),
        "device": str(device),
        "processor": processor,
        "model": model,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    adapter_path = os.getenv("STT_ADAPTER_PATH", DEFAULT_ADAPTER_PATH)
    adapter_resolved = _resolve_path(adapter_path)
    return {
        "status": "ok",
        "base_model": os.getenv("STT_BASE_MODEL", DEFAULT_BASE_MODEL),
        "adapter_path": str(adapter_resolved),
        "adapter_exists": adapter_resolved.exists(),
        "device": os.getenv("STT_DEVICE", "cuda"),
        "model_loaded": _load_model.cache_info().currsize > 0,
    }


@app.post("/warmup")
def warmup() -> dict[str, Any]:
    try:
        bundle = _load_model()
    except Exception as exc:  # pragma: no cover - depends on NAS GPU state
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "status": "loaded",
        "base_model": bundle["base_model"],
        "adapter_path": bundle["adapter_path"],
        "device": bundle["device"],
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("korean"),
    task: str = Form("transcribe"),
    max_new_tokens: int = Form(256),
    chunk_seconds: float = Form(DEFAULT_CHUNK_SECONDS),
    chunk_overlap_seconds: float = Form(DEFAULT_CHUNK_OVERLAP_SECONDS),
    min_chunk_rms: float = Form(DEFAULT_MIN_CHUNK_RMS),
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        bundle = _load_model()
    except Exception as exc:  # pragma: no cover - depends on NAS GPU state
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(await file.read())

    try:
        audio, sampling_rate, duration = _read_audio(temp_path)
        processor = bundle["processor"]
        chunks = _iter_audio_chunks(
            audio,
            sampling_rate=sampling_rate,
            chunk_seconds=chunk_seconds,
            chunk_overlap_seconds=chunk_overlap_seconds,
            min_chunk_rms=min_chunk_rms,
        )
        if not chunks:
            chunks = [
                {
                    "chunk_index": 0,
                    "start_sec": 0.0,
                    "end_sec": duration,
                    "audio": audio,
                    "rms": 0.0,
                }
            ]
        processor.tokenizer.set_prefix_tokens(language=language, task=task)
        segments: list[dict[str, Any]] = []
        raw_confidences: list[float] = []
        for chunk in chunks:
            text, avg_logprob, raw_confidence = _transcribe_audio_chunk(
                bundle=bundle,
                audio=chunk["audio"],
                sampling_rate=sampling_rate,
                language=language,
                task=task,
                max_new_tokens=max_new_tokens,
            )
            if not text:
                continue
            is_low_confidence = raw_confidence < float(os.getenv("STT_LOW_CONFIDENCE_THRESHOLD", "0.55"))
            raw_confidences.append(raw_confidence)
            segments.append(
                {
                    "segment_index": len(segments),
                    "chunk_index": chunk["chunk_index"],
                    "start_sec": chunk["start_sec"],
                    "end_sec": chunk["end_sec"],
                    "text": text,
                    "normalized_text": text,
                    "confidence": raw_confidence,
                    "raw_confidence": raw_confidence,
                    "calibrated_confidence": raw_confidence,
                    "avg_logprob": avg_logprob,
                    "no_speech_prob": None,
                    "tokens_json": None,
                    "is_low_confidence": is_low_confidence,
                    "rms": chunk["rms"],
                }
            )
    finally:
        temp_path.unlink(missing_ok=True)

    full_text = _normalize_text(" ".join(segment["text"] for segment in segments))
    average_confidence = statistics.fmean(raw_confidences) if raw_confidences else 0.0
    low_confidence_count = len([segment for segment in segments if segment["is_low_confidence"]])
    return {
        "language": "ko",
        "full_text": full_text,
        "normalized_text": full_text,
        "average_confidence": average_confidence,
        "average_raw_confidence": average_confidence,
        "average_calibrated_confidence": average_confidence,
        "calibration_applied": False,
        "diarization_applied": False,
        "speaker_count": 0,
        "speaker_turns": None,
        "low_confidence_ratio": (low_confidence_count / len(segments)) if segments else 0.0,
        "duration": duration,
        "segments": segments,
        "processed_audio_path": None,
        "chunking": {
            "enabled": duration > chunk_seconds,
            "chunk_seconds": chunk_seconds,
            "chunk_overlap_seconds": chunk_overlap_seconds,
            "min_chunk_rms": min_chunk_rms,
            "input_chunk_count": len(chunks),
            "output_segment_count": len(segments),
        },
        "model": {
            "base_model": bundle["base_model"],
            "adapter_path": bundle["adapter_path"],
            "device": bundle["device"],
        },
        "runtime_seconds": time.perf_counter() - started,
    }
