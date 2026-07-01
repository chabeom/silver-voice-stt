from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from jiwer import cer, wer

from training_pipeline.dataset import (
    _build_audio_index,
    _find_audio_file,
    extract_aihub_transcript,
    read_audio_duration,
    read_json_with_fallback,
    read_text_with_fallback,
    resolve_aihub_dataset_roots,
)


ALT_TEXT_PATTERN = re.compile(r"\(([^()/]+)\)/\(([^()/]+)\)")
NON_TEXT_PATTERN = re.compile(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ\s]")
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_for_metric(text: str) -> str:
    normalized = ALT_TEXT_PATTERN.sub(r"\1", str(text))
    normalized = NON_TEXT_PATTERN.sub(" ", normalized)
    return WHITESPACE_PATTERN.sub(" ", normalized).strip()


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def build_asr_pipeline(args: argparse.Namespace) -> Any:
    import torch
    from transformers import pipeline

    dtype_map = {
        "auto": "auto",
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    device = 0 if args.device.startswith("cuda") else -1
    return pipeline(
        "automatic-speech-recognition",
        model=args.model_name,
        device=device,
        torch_dtype=dtype_map[args.torch_dtype],
        chunk_length_s=args.chunk_length_seconds,
        stride_length_s=args.stride_length_seconds,
        batch_size=args.batch_size,
        model_kwargs={"local_files_only": args.local_files_only},
        tokenizer=args.model_name,
        feature_extractor=args.model_name,
    )


def load_existing_rows(report_path: Path) -> list[dict[str, Any]]:
    if not report_path.exists():
        return []
    return [
        json.loads(line)
        for line in report_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize(rows: list[dict[str, Any]], args: argparse.Namespace, started: float) -> dict[str, Any]:
    processed = [row for row in rows if row.get("status") == "processed"]
    passed = [row for row in processed if row.get("passed")]
    failed = [row for row in rows if row.get("status") == "failed"]
    skipped = [row for row in rows if row.get("status") == "skipped"]
    cers = [float(row["cer"]) for row in processed if row.get("cer") is not None]
    wers = [float(row["wer"]) for row in processed if row.get("wer") is not None]
    return {
        "dataset_root": str(Path(args.dataset_root).resolve()),
        "model_name": args.model_name,
        "transcript_mode": args.transcript_mode,
        "cer_threshold": args.cer_threshold,
        "wer_threshold": args.wer_threshold,
        "count": len(rows),
        "processed": len(processed),
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(skipped),
        "pass_rate": len(passed) / len(processed) if processed else 0.0,
        "runtime_seconds": time.perf_counter() - started,
        "cer_avg": statistics.fmean(cers) if cers else 0.0,
        "cer_median": statistics.median(cers) if cers else 0.0,
        "cer_p10": percentile(cers, 0.1),
        "cer_p90": percentile(cers, 0.9),
        "wer_avg": statistics.fmean(wers) if wers else 0.0,
        "wer_median": statistics.median(wers) if wers else 0.0,
        "wer_p10": percentile(wers, 0.1),
        "wer_p90": percentile(wers, 0.9),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate AI-Hub labels by transcribing each WAV and comparing text.")
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default="openai/whisper-large-v3")
    parser.add_argument("--transcript-mode", choices=["full", "answer", "question"], default="full")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--torch-dtype", choices=["auto", "float32", "float16", "bfloat16"], default="bfloat16")
    parser.add_argument("--language", default="korean")
    parser.add_argument("--task", default="transcribe")
    parser.add_argument("--chunk-length-seconds", type=float, default=30.0)
    parser.add_argument("--stride-length-seconds", type=float, default=5.0)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--cer-threshold", type=float, default=0.5)
    parser.add_argument("--wer-threshold", type=float)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "label_validation.jsonl"
    summary_path = output_dir / "label_validation_summary.json"
    passed_path = output_dir / "passed_labels.txt"
    failed_path = output_dir / "failed_labels.txt"

    existing_rows = [] if args.overwrite else load_existing_rows(report_path)
    processed_label_paths = {row.get("label_path") for row in existing_rows if row.get("label_path")}
    rows = existing_rows[:]

    source_root, label_root = resolve_aihub_dataset_roots(args.dataset_root)
    audio_index = _build_audio_index(source_root)
    label_paths = sorted(label_root.rglob("*.json"))
    if args.limit is not None:
        label_paths = label_paths[: args.limit]

    asr = build_asr_pipeline(args)
    report_file_mode = "w" if args.overwrite else "a"
    with report_path.open(report_file_mode, encoding="utf-8") as report_file:
        for index, label_path in enumerate(label_paths, start=1):
            resolved_label_path = str(label_path.resolve())
            if resolved_label_path in processed_label_paths:
                print(f"[{index}/{len(label_paths)}] skipped existing: {label_path.name}", flush=True)
                continue

            try:
                relative_path = label_path.relative_to(label_root)
                payload = read_json_with_fallback(label_path)
                audio_path = _find_audio_file(source_root, relative_path, payload, audio_index)
                if audio_path is None:
                    row = {
                        "status": "skipped",
                        "reason": "audio not found",
                        "label_path": resolved_label_path,
                        "relative_label_path": str(relative_path),
                    }
                else:
                    transcript_path = (source_root / relative_path).with_suffix(".txt")
                    raw_transcript = read_text_with_fallback(transcript_path) if transcript_path.exists() else None
                    label_text = extract_aihub_transcript(
                        payload,
                        raw_transcript,
                        transcript_mode=args.transcript_mode,
                    )
                    if not label_text:
                        row = {
                            "status": "skipped",
                            "reason": "empty label text",
                            "label_path": resolved_label_path,
                            "relative_label_path": str(relative_path),
                            "audio_path": str(audio_path.resolve()),
                        }
                    else:
                        result = asr(
                            str(audio_path),
                            generate_kwargs={"language": args.language, "task": args.task},
                        )
                        stt_text = result["text"] if isinstance(result, dict) else str(result)
                        reference = normalize_for_metric(label_text)
                        prediction = normalize_for_metric(stt_text)
                        sample_cer = float(cer(reference, prediction)) if reference else 1.0
                        sample_wer = float(wer(reference, prediction)) if reference else 1.0
                        passed = sample_cer <= args.cer_threshold and (
                            args.wer_threshold is None or sample_wer <= args.wer_threshold
                        )
                        row = {
                            "status": "processed",
                            "passed": passed,
                            "label_path": resolved_label_path,
                            "relative_label_path": str(relative_path),
                            "audio_path": str(audio_path.resolve()),
                            "duration_sec": read_audio_duration(audio_path),
                            "audio_time": payload.get("audioTime"),
                            "json_id": payload.get("jsonId"),
                            "qa_count": len(payload.get("qa", [])) if isinstance(payload.get("qa"), list) else None,
                            "label_text": label_text,
                            "stt_text": stt_text,
                            "normalized_label_text": reference,
                            "normalized_stt_text": prediction,
                            "cer": sample_cer,
                            "wer": sample_wer,
                        }
                report_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                report_file.flush()
                rows.append(row)
                if row.get("status") == "processed":
                    print(
                        f"[{index}/{len(label_paths)}] passed={row['passed']} cer={row['cer']:.4f} wer={row['wer']:.4f} {label_path.name}",
                        flush=True,
                    )
                else:
                    print(f"[{index}/{len(label_paths)}] {row['status']}: {row.get('reason')} {label_path.name}", flush=True)
            except Exception as exc:
                row = {
                    "status": "failed",
                    "reason": str(exc),
                    "label_path": resolved_label_path,
                    "relative_label_path": str(label_path.relative_to(label_root)),
                }
                report_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                report_file.flush()
                rows.append(row)
                print(f"[{index}/{len(label_paths)}] failed: {exc} {label_path.name}", flush=True)

    passed_rows = [row for row in rows if row.get("status") == "processed" and row.get("passed")]
    failed_rows = [row for row in rows if row.get("status") != "processed" or not row.get("passed")]
    passed_path.write_text("\n".join(row["label_path"] for row in passed_rows) + ("\n" if passed_rows else ""), encoding="utf-8")
    failed_path.write_text("\n".join(row.get("label_path", "") for row in failed_rows if row.get("label_path")) + ("\n" if failed_rows else ""), encoding="utf-8")
    summary = summarize(rows, args, started)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
