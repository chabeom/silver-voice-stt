from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from jiwer import cer, wer


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def load_manifest(path: Path, max_samples: int | None) -> list[dict[str, Any]]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    return records[:max_samples] if max_samples is not None else records


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    from math import gcd

    import numpy as np
    import soundfile as sf
    import torch
    from peft import PeftModel
    from scipy.signal import resample_poly
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    records = load_manifest(Path(args.manifest), args.max_samples)
    processor = WhisperProcessor.from_pretrained(args.adapter_path, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(args.base_model, local_files_only=True)
    model = PeftModel.from_pretrained(model, args.adapter_path, local_files_only=True)
    model.eval()

    device = torch.device(args.device)
    model.to(device)
    references: list[str] = []
    predictions: list[str] = []
    raw_confidences: list[float] = []
    sample_results: list[dict[str, Any]] = []
    started = time.perf_counter()

    for index, record in enumerate(records, start=1):
        audio_path = Path(record["audio_path"])
        audio, sampling_rate = sf.read(audio_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sampling_rate != 16000:
            common = gcd(sampling_rate, 16000)
            audio = resample_poly(audio, 16000 // common, sampling_rate // common).astype(np.float32)
            sampling_rate = 16000
        inputs = processor.feature_extractor(
            audio,
            sampling_rate=sampling_rate,
            return_tensors="pt",
        )
        input_features = inputs.input_features.to(device)

        with torch.inference_mode():
            generated = model.generate(
                input_features,
                language=args.language,
                task="transcribe",
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
        predicted_text = normalize_text(
            processor.tokenizer.decode(generated.sequences[0], skip_special_tokens=True)
        )
        reference_text = normalize_text(str(record["text"]))
        sample_cer = float(cer(reference_text, predicted_text))
        references.append(reference_text)
        predictions.append(predicted_text)
        raw_confidences.append(raw_confidence)
        sample_results.append(
            {
                "sample_id": record.get("sample_id"),
                "audio_path": str(audio_path),
                "duration_sec": record.get("duration_sec"),
                "reference_text": reference_text,
                "predicted_text": predicted_text,
                "avg_logprob": avg_logprob,
                "raw_confidence": raw_confidence,
                "cer": sample_cer,
                "success_cer_le_0_1": sample_cer <= 0.1,
                "exact_match": reference_text == predicted_text,
            }
        )
        print(
            f"[{index}/{len(records)}] confidence={raw_confidence:.4f} cer={sample_cer:.4f}",
            flush=True,
        )

    success_count = sum(item["success_cer_le_0_1"] for item in sample_results)
    exact_match_count = sum(item["exact_match"] for item in sample_results)
    low_confidence_count = sum(confidence < args.low_confidence_threshold for confidence in raw_confidences)
    summary = {
        "model": str(Path(args.adapter_path).resolve()),
        "base_model": args.base_model,
        "manifest": str(Path(args.manifest).resolve()),
        "sample_count": len(sample_results),
        "runtime_seconds": time.perf_counter() - started,
        "average_raw_confidence": statistics.fmean(raw_confidences) if raw_confidences else 0.0,
        "median_raw_confidence": statistics.median(raw_confidences) if raw_confidences else 0.0,
        "raw_confidence_p10": percentile(raw_confidences, 0.1),
        "raw_confidence_p90": percentile(raw_confidences, 0.9),
        "low_confidence_threshold": args.low_confidence_threshold,
        "low_confidence_ratio": low_confidence_count / len(sample_results) if sample_results else 0.0,
        "cer_le_0_1_success_rate": success_count / len(sample_results) if sample_results else 0.0,
        "exact_match_rate": exact_match_count / len(sample_results) if sample_results else 0.0,
        "cer": float(cer(references, predictions)),
        "wer": float(wer(references, predictions)),
    }
    return {"summary": summary, "samples": sample_results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a Whisper LoRA model's raw confidence.")
    parser.add_argument("--adapter-path", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--base-model", default="openai/whisper-tiny")
    parser.add_argument("--language", default="korean")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--low-confidence-threshold", type=float, default=0.55)
    args = parser.parse_args()

    result = evaluate(args)
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
