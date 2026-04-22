import argparse
import json
from pathlib import Path

from training_pipeline.dataset import iter_aihub_sample_records, resolve_aihub_dataset_roots
from training_pipeline.manifest import summarize_records, train_valid_test_split, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--speaker-type", default="elderly_or_disordered")
    parser.add_argument("--source-name", default="aihub_sample")
    parser.add_argument("--valid-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--group-key", default="speaker_id")
    parser.add_argument("--min-duration-seconds", type=float, default=0.3)
    parser.add_argument("--max-duration-seconds", type=float, default=30.0)
    parser.add_argument("--target-segment-seconds", type=float, default=28.0)
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
        )
    )
    splits = train_valid_test_split(
        records,
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
        "total": summarize_records(records),
        "splits": {split_name: summarize_records(split_records) for split_name, split_records in splits.items()},
        "segmented_long_audio": not args.disable_long_audio_segmentation,
    }
    (output_dir / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
