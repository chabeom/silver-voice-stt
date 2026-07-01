import argparse
import json
from pathlib import Path

from training_pipeline.dataset import iter_aihub_sample_records, resolve_aihub_dataset_roots
from training_pipeline.manifest import summarize_records, train_valid_test_split, write_jsonl


def non_space_len(text: str) -> int:
    return len("".join(str(text).split()))


def filter_records_by_quality(
    records: list[dict],
    *,
    min_text_chars: int | None,
    max_text_chars: int | None,
    min_chars_per_second: float | None,
    max_chars_per_second: float | None,
) -> tuple[list[dict], dict[str, int]]:
    kept: list[dict] = []
    skipped = {
        "too_short_text": 0,
        "too_long_text": 0,
        "too_low_chars_per_second": 0,
        "too_high_chars_per_second": 0,
    }

    for record in records:
        text_length = non_space_len(record.get("text") or "")
        duration_sec = float(record.get("duration_sec") or 0.0)

        if min_text_chars is not None and text_length < min_text_chars:
            skipped["too_short_text"] += 1
            continue
        if max_text_chars is not None and text_length > max_text_chars:
            skipped["too_long_text"] += 1
            continue

        if duration_sec > 0:
            chars_per_second = text_length / duration_sec
            if min_chars_per_second is not None and chars_per_second < min_chars_per_second:
                skipped["too_low_chars_per_second"] += 1
                continue
            if max_chars_per_second is not None and chars_per_second > max_chars_per_second:
                skipped["too_high_chars_per_second"] += 1
                continue

        kept.append(record)

    return kept, skipped


def load_validation_allowed_labels(
    report_path: str | None,
    *,
    passed_only: bool,
    max_cer: float | None,
    max_wer: float | None,
) -> set[str] | None:
    if not report_path:
        return None

    allowed: set[str] = set()
    with Path(report_path).open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status") != "processed":
                continue
            if passed_only and not row.get("passed"):
                continue
            if max_cer is not None and float(row.get("cer", 999.0)) > max_cer:
                continue
            if max_wer is not None and float(row.get("wer", 999.0)) > max_wer:
                continue
            label_path = row.get("label_path")
            if label_path:
                allowed.add(str(Path(label_path).resolve()))
    return allowed


def filter_records_by_validation(records: list[dict], allowed_labels: set[str] | None) -> tuple[list[dict], int]:
    if allowed_labels is None:
        return records, 0

    kept: list[dict] = []
    skipped = 0
    for record in records:
        label_path = (record.get("metadata") or {}).get("label_path")
        if label_path and str(Path(label_path).resolve()) in allowed_labels:
            kept.append(record)
        else:
            skipped += 1
    return kept, skipped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--speaker-type", default="elderly_or_disordered")
    parser.add_argument("--source-name", default="aihub_sample")
    parser.add_argument("--transcript-mode", choices=["full", "answer", "question"], default="full")
    parser.add_argument("--valid-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--group-key", default="speaker_id")
    parser.add_argument("--min-duration-seconds", type=float, default=0.3)
    parser.add_argument("--max-duration-seconds", type=float, default=30.0)
    parser.add_argument("--target-segment-seconds", type=float, default=28.0)
    parser.add_argument("--max-segment-chars", type=int, default=240)
    parser.add_argument("--min-text-chars", type=int)
    parser.add_argument("--max-text-chars", type=int)
    parser.add_argument("--min-chars-per-second", type=float)
    parser.add_argument("--max-chars-per-second", type=float)
    parser.add_argument("--validation-report")
    parser.add_argument("--validation-passed-only", action="store_true")
    parser.add_argument("--max-validation-cer", type=float)
    parser.add_argument("--max-validation-wer", type=float)
    parser.add_argument("--disable-long-audio-segmentation", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source_root, label_root = resolve_aihub_dataset_roots(Path(args.dataset_root))
    records = list(
        iter_aihub_sample_records(
            args.dataset_root,
            speaker_type=args.speaker_type,
            source_name=args.source_name,
            min_duration_seconds=args.min_duration_seconds,
            max_duration_seconds=args.max_duration_seconds,
            segment_long_audio=not args.disable_long_audio_segmentation,
            segment_audio_dir=Path(args.output_dir) / "clips",
            target_segment_seconds=args.target_segment_seconds,
            max_segment_chars=args.max_segment_chars,
            transcript_mode=args.transcript_mode,
        )
    )
    allowed_labels = load_validation_allowed_labels(
        args.validation_report,
        passed_only=args.validation_passed_only,
        max_cer=args.max_validation_cer,
        max_wer=args.max_validation_wer,
    )
    validation_filtered_records, skipped_by_validation = filter_records_by_validation(records, allowed_labels)
    filtered_records, skipped_by_quality = filter_records_by_quality(
        validation_filtered_records,
        min_text_chars=args.min_text_chars,
        max_text_chars=args.max_text_chars,
        min_chars_per_second=args.min_chars_per_second,
        max_chars_per_second=args.max_chars_per_second,
    )
    splits = train_valid_test_split(
        filtered_records,
        seed=args.seed,
        valid_ratio=args.valid_ratio,
        test_ratio=args.test_ratio,
        group_key=args.group_key,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for split_name, split_records in splits.items():
        write_jsonl(split_records, str(output_dir / f"{split_name}.jsonl"))

    summary = {
        "dataset_root": str(Path(args.dataset_root)),
        "resolved_source_root": str(source_root),
        "resolved_label_root": str(label_root),
        "transcript_mode": args.transcript_mode,
        "total_before_quality_filter": summarize_records(records),
        "total_after_validation_filter": summarize_records(validation_filtered_records),
        "total": summarize_records(filtered_records),
        "splits": {split_name: summarize_records(split_records) for split_name, split_records in splits.items()},
        "segmented_long_audio": not args.disable_long_audio_segmentation,
        "max_segment_chars": args.max_segment_chars,
        "quality_filter": {
            "min_text_chars": args.min_text_chars,
            "max_text_chars": args.max_text_chars,
            "min_chars_per_second": args.min_chars_per_second,
            "max_chars_per_second": args.max_chars_per_second,
            "skipped": skipped_by_quality,
        },
        "validation_filter": {
            "validation_report": args.validation_report,
            "validation_passed_only": args.validation_passed_only,
            "max_validation_cer": args.max_validation_cer,
            "max_validation_wer": args.max_validation_wer,
            "allowed_label_count": len(allowed_labels) if allowed_labels is not None else None,
            "skipped_records": skipped_by_validation,
        },
    }
    (output_dir / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
