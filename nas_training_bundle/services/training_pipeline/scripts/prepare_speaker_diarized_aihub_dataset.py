from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from training_pipeline.dataset import normalize_transcript_text, read_json_with_fallback, resolve_aihub_dataset_roots
from training_pipeline.diarization import (
    choose_longest_speaker,
    chunk_turns,
    merge_speaker_turns,
    split_text_by_weights,
    write_concatenated_wav,
)
from training_pipeline.manifest import load_jsonl, summarize_records, train_valid_test_split, write_jsonl


SUPPORTED_AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a"}


def extract_answer_text(payload: dict[str, Any]) -> str:
    qa = payload.get("qa")
    if not isinstance(qa, list):
        return ""
    answers = [
        normalize_transcript_text(str(turn.get("answer") or ""))
        for turn in qa
        if isinstance(turn, dict)
    ]
    return " ".join(answer for answer in answers if answer).strip()


def serialize_diarization(output: Any) -> list[dict[str, float | str]]:
    diarization = getattr(output, "exclusive_speaker_diarization", None)
    if diarization is None:
        diarization = getattr(output, "speaker_diarization", None)
    if diarization is None:
        diarization = output
    turns: list[dict[str, float | str]] = []
    if hasattr(diarization, "itertracks"):
        iterator = ((turn, speaker) for turn, _, speaker in diarization.itertracks(yield_label=True))
    else:
        iterator = iter(diarization)

    for turn, speaker in iterator:
        turns.append(
            {
                "speaker": str(speaker),
                "start_sec": round(float(turn.start), 3),
                "end_sec": round(float(turn.end), 3),
            }
        )
    return turns


def build_audio_index(source_root: Path) -> dict[str, Path]:
    return {
        path.name: path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diarize AI-Hub conversations and build an elderly-speaker-only training manifest."
    )
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default="pyannote/speaker-diarization-community-1")
    parser.add_argument("--hf-token", default=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN"))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--num-speakers", type=int, default=2)
    parser.add_argument("--target-speaker", default="longest", help="'longest' or a pyannote speaker label.")
    parser.add_argument("--max-chunk-seconds", type=float, default=28.0)
    parser.add_argument("--merge-gap-seconds", type=float, default=0.35)
    parser.add_argument("--min-turn-seconds", type=float, default=0.3)
    parser.add_argument("--valid-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.hf_token:
        raise ValueError("Set HF_TOKEN after accepting the pyannote model conditions on Hugging Face.")

    import torch
    from pyannote.audio import Pipeline

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable. Run the NAS GPU check first.")

    source_root, label_root = resolve_aihub_dataset_roots(args.dataset_root)
    audio_index = build_audio_index(source_root)
    output_dir = Path(args.output_dir)
    clip_dir = output_dir / "clips"
    report_dir = output_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline.from_pretrained(args.model_name, token=args.hf_token)
    pipeline.to(torch.device(args.device))

    existing_manifest_paths = [output_dir / f"{split}.jsonl" for split in ("train", "valid", "test")]
    records: list[dict[str, Any]] = []
    if not args.overwrite:
        for manifest_path in existing_manifest_paths:
            if manifest_path.exists():
                records.extend(load_jsonl(manifest_path))
    reports: list[dict[str, Any]] = []
    label_paths = sorted(label_root.rglob("*.json"))
    if args.limit is not None:
        label_paths = label_paths[: args.limit]

    for label_path in label_paths:
        payload = read_json_with_fallback(label_path)
        audio_name = str(payload.get("audioFile") or label_path.with_suffix(".wav").name)
        audio_path = audio_index.get(audio_name)
        answer_text = extract_answer_text(payload)
        if audio_path is None or not answer_text:
            reports.append({"label_path": str(label_path), "status": "skipped", "reason": "audio or answer text missing"})
            continue

        sample_id = str(payload.get("jsonId") or audio_path.stem)
        report_path = report_dir / f"{audio_path.stem}.json"
        if report_path.exists() and not args.overwrite:
            existing_report = json.loads(report_path.read_text(encoding="utf-8"))
            if existing_report.get("status") == "processed":
                reports.append(existing_report)
                print(f"skipped existing report: {audio_path.name}")
                continue

        try:
            output = pipeline(str(audio_path), num_speakers=args.num_speakers)
            turns = serialize_diarization(output)
            selected_speaker = choose_longest_speaker(turns) if args.target_speaker == "longest" else args.target_speaker
            selected_turns = merge_speaker_turns(
                turns,
                speaker=selected_speaker,
                merge_gap_seconds=args.merge_gap_seconds,
                min_turn_seconds=args.min_turn_seconds,
            )
            chunks = chunk_turns(selected_turns, max_chunk_seconds=args.max_chunk_seconds)
            chunk_weights = [
                sum(float(turn["end_sec"]) - float(turn["start_sec"]) for turn in chunk)
                for chunk in chunks
            ]
            chunk_texts = split_text_by_weights(answer_text, chunk_weights)

            for chunk_index, (chunk, text) in enumerate(zip(chunks, chunk_texts)):
                clip_path = clip_dir / audio_path.stem / f"{audio_path.stem}__elderly_{chunk_index:04d}.wav"
                duration = write_concatenated_wav(audio_path, clip_path, chunk)
                if duration < args.min_turn_seconds or not text:
                    continue
                records.append(
                    {
                        "sample_id": f"{sample_id}-elderly-{chunk_index:04d}",
                        "audio_path": str(clip_path.resolve()),
                        "text": text,
                        "speaker_id": f"{sample_id}:{selected_speaker}",
                        "speaker_type": "elderly",
                        "source": "aihub_speaker_diarized",
                        "duration_sec": duration,
                        "metadata": {
                            "original_audio_path": str(audio_path),
                            "label_path": str(label_path),
                            "diarized_speaker": selected_speaker,
                            "speaker_selection": args.target_speaker,
                            "alignment_quality": "approximate_answer_text_by_duration",
                            "requires_manual_review": True,
                            "source_turns": chunk,
                        },
                    }
                )

            report = {
                "sample_id": sample_id,
                "audio_path": str(audio_path),
                "label_path": str(label_path),
                "selected_speaker": selected_speaker,
                "speaker_durations": {
                    speaker: round(
                        sum(float(turn["end_sec"]) - float(turn["start_sec"]) for turn in turns if turn["speaker"] == speaker),
                        3,
                    )
                    for speaker in sorted({str(turn["speaker"]) for turn in turns})
                },
                "turns": turns,
                "status": "processed",
            }
            reports.append(report)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"processed {audio_path.name}: selected {selected_speaker}, chunks={len(chunks)}")
        except Exception as exc:
            report = {
                "sample_id": sample_id,
                "audio_path": str(audio_path),
                "label_path": str(label_path),
                "status": "failed",
                "reason": str(exc),
            }
            reports.append(report)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"failed {audio_path.name}: {exc}")

    splits = train_valid_test_split(
        records,
        valid_ratio=args.valid_ratio,
        test_ratio=args.test_ratio,
        group_key="speaker_id",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(reports, str(output_dir / "diarization.jsonl"))
    for split_name, split_records in splits.items():
        write_jsonl(split_records, str(output_dir / f"{split_name}.jsonl"))

    summary = {
        "dataset_root": str(Path(args.dataset_root)),
        "model_name": args.model_name,
        "target_speaker": args.target_speaker,
        "num_speakers": args.num_speakers,
        "alignment_quality": "approximate_answer_text_by_duration",
        "requires_manual_review": True,
        "total": summarize_records(records),
        "splits": {name: summarize_records(items) for name, items in splits.items()},
        "processed_files": sum(1 for report in reports if report.get("status") == "processed"),
        "skipped_files": sum(1 for report in reports if report.get("status") == "skipped"),
        "failed_files": sum(1 for report in reports if report.get("status") == "failed"),
    }
    (output_dir / "dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
