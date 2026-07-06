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
from fastapi.responses import HTMLResponse


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


def _render_test_ui() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Silver Voice STT Test</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #dbeafe;
      --sky: #0284c7;
      --blue: #2563eb;
      --bg: #eef7ff;
      --card: rgba(255,255,255,.86);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 20%, rgba(56,189,248,.25), transparent 32rem),
        radial-gradient(circle at 85% 10%, rgba(37,99,235,.18), transparent 28rem),
        linear-gradient(135deg, #f8fbff 0%, var(--bg) 100%);
    }
    main {
      width: min(980px, calc(100% - 32px));
      margin: 0 auto;
      padding: 44px 0;
    }
    .hero {
      display: grid;
      gap: 12px;
      margin-bottom: 24px;
    }
    .kicker {
      margin: 0;
      color: var(--blue);
      font-size: 13px;
      font-weight: 800;
      letter-spacing: .22em;
      text-transform: uppercase;
    }
    h1 {
      margin: 0;
      max-width: 760px;
      font-size: clamp(36px, 7vw, 74px);
      line-height: .94;
      letter-spacing: -.06em;
    }
    .copy {
      max-width: 720px;
      margin: 0;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.75;
    }
    .card {
      border: 1px solid rgba(125, 211, 252, .55);
      border-radius: 34px;
      background: var(--card);
      box-shadow: 0 28px 80px rgba(37, 99, 235, .13);
      backdrop-filter: blur(18px);
      padding: clamp(20px, 4vw, 34px);
    }
    .drop {
      display: grid;
      place-items: center;
      min-height: 230px;
      border: 2px dashed #93c5fd;
      border-radius: 28px;
      background: rgba(239, 246, 255, .78);
      text-align: center;
      transition: .18s ease;
    }
    .drop.dragging {
      border-color: var(--blue);
      background: rgba(191, 219, 254, .75);
      transform: translateY(-2px);
    }
    .drop strong {
      display: block;
      font-size: 22px;
      margin-bottom: 8px;
    }
    .drop span {
      color: var(--muted);
      line-height: 1.6;
    }
    input[type=file] {
      margin-top: 22px;
      width: min(100%, 560px);
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
      padding: 14px;
      font-size: 15px;
    }
    .controls {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      margin-top: 18px;
    }
    button {
      border: 0;
      border-radius: 18px;
      padding: 16px 18px;
      color: white;
      background: linear-gradient(135deg, var(--blue), #06b6d4);
      font-size: 16px;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 16px 34px rgba(37, 99, 235, .22);
    }
    button.secondary {
      color: var(--ink);
      background: white;
      border: 1px solid var(--line);
      box-shadow: none;
    }
    button:disabled {
      cursor: not-allowed;
      opacity: .55;
    }
    .status {
      margin-top: 18px;
      padding: 16px 18px;
      border-radius: 18px;
      background: #0f172a;
      color: white;
      line-height: 1.6;
      white-space: pre-wrap;
    }
    .result {
      margin-top: 22px;
      display: grid;
      gap: 16px;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 24px;
      background: rgba(255,255,255,.82);
      padding: 20px;
    }
    .panel h2 {
      margin: 0 0 10px;
      font-size: 17px;
      text-transform: uppercase;
      letter-spacing: .16em;
      color: var(--sky);
    }
    .text {
      margin: 0;
      font-size: 18px;
      line-height: 1.9;
      white-space: pre-wrap;
    }
    .segment {
      border-top: 1px solid var(--line);
      padding: 13px 0;
      line-height: 1.75;
    }
    .segment:first-of-type { border-top: 0; }
    .meta {
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <p class="kicker">Silver Voice NAS GPU</p>
      <h1>STT inference test</h1>
      <p class="copy">Upload an elderly speaker audio file here. This page calls the NAS inference API directly, so it does not need the full Next.js frontend, login, or npm.</p>
    </section>
    <section class="card">
      <div id="drop" class="drop">
        <div>
          <strong>Drag and drop an audio file</strong>
          <span>or select wav, mp3, m4a, webm, mp4, flac, aac, ogg.</span>
          <br />
          <input id="file" type="file" accept="audio/*" />
        </div>
      </div>
      <div class="controls">
        <button id="transcribe" disabled>Run STT</button>
        <button id="warmup" class="secondary">Warm up model</button>
        <button id="health" class="secondary">Check health</button>
      </div>
      <div id="status" class="status">Waiting for an audio file.</div>
      <div id="result" class="result"></div>
    </section>
  </main>
  <script>
    const fileInput = document.querySelector("#file");
    const drop = document.querySelector("#drop");
    const button = document.querySelector("#transcribe");
    const warmupButton = document.querySelector("#warmup");
    const healthButton = document.querySelector("#health");
    const statusBox = document.querySelector("#status");
    const resultBox = document.querySelector("#result");
    let selectedFile = null;

    function setStatus(message) {
      statusBox.textContent = message;
    }

    function selectFile(file) {
      selectedFile = file;
      button.disabled = !file;
      resultBox.innerHTML = "";
      setStatus(file ? `Selected: ${file.name} (${Math.round(file.size / 1024 / 1024 * 10) / 10} MB)` : "Waiting for an audio file.");
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      })[char]);
    }

    async function callJson(path, options = {}) {
      const response = await fetch(path, options);
      const text = await response.text();
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = { raw: text };
      }
      if (!response.ok) {
        throw new Error(JSON.stringify(data, null, 2));
      }
      return data;
    }

    function renderResult(data) {
      const segments = data.segments || [];
      resultBox.innerHTML = `
        <article class="panel">
          <h2>Full text</h2>
          <p class="text">${escapeHtml(data.full_text || "")}</p>
        </article>
        <article class="panel">
          <h2>Summary</h2>
          <p class="text">Duration: ${Number(data.duration || 0).toFixed(1)}s
Runtime: ${Number(data.runtime_seconds || 0).toFixed(1)}s
Confidence: ${Number(data.average_confidence || 0).toFixed(3)}
Segments: ${segments.length}</p>
        </article>
        <article class="panel">
          <h2>Segments</h2>
          ${segments.map((segment) => `
            <div class="segment">
              <div class="meta">${Number(segment.start_sec || 0).toFixed(1)}s - ${Number(segment.end_sec || 0).toFixed(1)}s | confidence ${Number(segment.confidence || 0).toFixed(3)}</div>
              <div>${escapeHtml(segment.text || "")}</div>
            </div>
          `).join("")}
        </article>
      `;
    }

    fileInput.addEventListener("change", () => selectFile(fileInput.files?.[0] || null));

    ["dragenter", "dragover"].forEach((name) => {
      drop.addEventListener(name, (event) => {
        event.preventDefault();
        drop.classList.add("dragging");
      });
    });
    ["dragleave", "drop"].forEach((name) => {
      drop.addEventListener(name, (event) => {
        event.preventDefault();
        drop.classList.remove("dragging");
      });
    });
    drop.addEventListener("drop", (event) => {
      const file = Array.from(event.dataTransfer.files || []).find((item) => item.type.startsWith("audio/") || /\.(wav|mp3|m4a|webm|mp4|flac|aac|ogg)$/i.test(item.name));
      selectFile(file || null);
    });

    healthButton.addEventListener("click", async () => {
      try {
        setStatus("Checking health...");
        const data = await callJson("./health");
        setStatus(JSON.stringify(data, null, 2));
      } catch (error) {
        setStatus(`Health failed:\\n${error.message}`);
      }
    });

    warmupButton.addEventListener("click", async () => {
      try {
        setStatus("Loading model on GPU. This can take a moment...");
        const data = await callJson("./warmup", { method: "POST" });
        setStatus(JSON.stringify(data, null, 2));
      } catch (error) {
        setStatus(`Warmup failed:\\n${error.message}`);
      }
    });

    button.addEventListener("click", async () => {
      if (!selectedFile) return;
      const form = new FormData();
      form.append("file", selectedFile);
      form.append("chunk_seconds", "30");
      form.append("chunk_overlap_seconds", "0");
      form.append("max_new_tokens", "256");
      try {
        button.disabled = true;
        setStatus("Running STT on NAS GPU...");
        const data = await callJson("./transcribe", { method: "POST", body: form });
        setStatus("STT completed.");
        renderResult(data);
      } catch (error) {
        setStatus(`STT failed:\\n${error.message}`);
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>"""


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


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_ui() -> HTMLResponse:
    return HTMLResponse(_render_test_ui())


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def test_ui() -> HTMLResponse:
    return HTMLResponse(_render_test_ui())


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
