from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from math import gcd
from pathlib import Path
from typing import Any

from jiwer import cer, wer


def normalize_text(text: str) -> str:
    return " ".join(str(text).strip().split())


def load_manifest(path: Path, max_samples: int | None) -> list[dict[str, Any]]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    return records[:max_samples] if max_samples is not None else records


def read_audio(audio_path: Path) -> tuple[Any, int]:
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
    return audio, sampling_rate


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    records = load_manifest(Path(args.manifest), args.max_samples)
    processor_source = args.adapter_path or args.model_name_or_path
    processor = WhisperProcessor.from_pretrained(processor_source, local_files_only=args.local_files_only)
    processor.tokenizer.set_prefix_tokens(language=args.language, task=args.task)

    model = WhisperForConditionalGeneration.from_pretrained(
        args.model_name_or_path,
        local_files_only=args.local_files_only,
    )
    if args.adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(
            model,
            args.adapter_path,
            local_files_only=args.local_files_only,
        )

    device = torch.device(args.device)
    model.to(device)
    model.eval()

    references: list[str] = []
    predictions: list[str] = []
    raw_confidences: list[float] = []
    sample_results: list[dict[str, Any]] = []
    started = time.perf_counter()

    prediction_manifest_path = Path(args.prediction_manifest) if args.prediction_manifest else None
    prediction_rows: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        audio_path = Path(record["audio_path"])
        audio, sampling_rate = read_audio(audio_path)
        inputs = processor.feature_extractor(audio, sampling_rate=sampling_rate, return_tensors="pt")
        input_features = inputs.input_features.to(device)

        with torch.inference_mode():
            generated = model.generate(
                input_features,
                language=args.language,
                task=args.task,
                max_new_tokens=args.max_new_tokens,
                return_dict_in_generate=True,
                output_scores=True,
            )
            transition_scores = model.compute_transition_scores(
                generated.sequences,
                generated.scores,
                normalize_logits=True,
            )

        token_scores = transition_scores[0].detach().float().cpu().tolist()
        finite_scores = [score for score in token_scores if math.isfinite(score)]
        avg_logprob = statistics.fmean(finite_scores) if finite_scores else float("-inf")
        raw_confidence = math.exp(min(0.0, avg_logprob)) if math.isfinite(avg_logprob) else 0.0
        predicted_text = normalize_text(processor.tokenizer.decode(generated.sequences[0], skip_special_tokens=True))
        reference_text = normalize_text(record["text"])
        sample_cer = float(cer(reference_text, predicted_text))
        sample_wer = float(wer(reference_text, predicted_text))

        references.append(reference_text)
        predictions.append(predicted_text)
        raw_confidences.append(raw_confidence)
        sample_result = {
            "sample_id": record.get("sample_id"),
            "audio_path": str(audio_path),
            "duration_sec": record.get("duration_sec"),
            "reference_text": reference_text,
            "predicted_text": predicted_text,
            "avg_logprob": avg_logprob,
            "raw_confidence": raw_confidence,
            "wer": sample_wer,
            "cer": sample_cer,
        }
        sample_results.append(sample_result)
        prediction_rows.append({**record, "text": predicted_text})
        print(
            f"[{index}/{len(records)}] wer={sample_wer:.4f} cer={sample_cer:.4f} confidence={raw_confidence:.4f}",
            flush=True,
        )

    if prediction_manifest_path is not None:
        prediction_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with prediction_manifest_path.open("w", encoding="utf-8") as file:
            for row in prediction_rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "model_name_or_path": args.model_name_or_path,
        "adapter_path": args.adapter_path,
        "manifest": str(Path(args.manifest).resolve()),
        "sample_count": len(sample_results),
        "runtime_seconds": time.perf_counter() - started,
        "wer": float(wer(references, predictions)) if references else 0.0,
        "cer": float(cer(references, predictions)) if references else 0.0,
        "average_raw_confidence": statistics.fmean(raw_confidences) if raw_confidences else 0.0,
        "median_raw_confidence": statistics.median(raw_confidences) if raw_confidences else 0.0,
        "raw_confidence_p10": percentile(raw_confidences, 0.1),
        "raw_confidence_p90": percentile(raw_confidences, 0.9),
    }
    return {"summary": summary, "samples": sample_results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a manifest with Whisper and compute WER/CER.")
    parser.add_argument("--model-name-or-path", default="openai/whisper-large-v3")
    parser.add_argument("--adapter-path")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--prediction-manifest")
    parser.add_argument("--language", default="korean")
    parser.add_argument("--task", default="transcribe")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()

    result = evaluate(args)
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
