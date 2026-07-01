from __future__ import annotations

import json
import random
from pathlib import Path


def write_jsonl(records: list[dict], output_path: str) -> None:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: str | Path) -> list[dict]:
    target = Path(path)
    with target.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def summarize_records(records: list[dict]) -> dict:
    total_duration = sum(float(record.get("duration_sec") or 0.0) for record in records)
    by_source: dict[str, int] = {}
    by_speaker_type: dict[str, int] = {}

    for record in records:
        source = record.get("source") or "unknown"
        speaker_type = record.get("speaker_type") or "unknown"
        by_source[source] = by_source.get(source, 0) + 1
        by_speaker_type[speaker_type] = by_speaker_type.get(speaker_type, 0) + 1

    return {
        "count": len(records),
        "duration_hours": round(total_duration / 3600, 4),
        "average_duration_sec": round(total_duration / len(records), 4) if records else 0.0,
        "sources": by_source,
        "speaker_types": by_speaker_type,
    }


def _record_group_key(record: dict, group_key: str | None) -> str:
    if group_key:
        value = record.get(group_key)
        if value is None and isinstance(record.get("metadata"), dict):
            value = record["metadata"].get(group_key)
        if value not in (None, ""):
            return str(value)
    return str(record.get("sample_id") or record.get("audio_path"))


def _target_size(total: int, ratio: float, *, ensure_one: bool) -> int:
    if total <= 0 or ratio <= 0:
        return 0
    target = round(total * ratio)
    if ensure_one and total >= 3:
        return max(1, target)
    return max(0, target)


def train_valid_test_split(
    records: list[dict],
    *,
    seed: int = 42,
    valid_ratio: float = 0.1,
    test_ratio: float = 0.1,
    group_key: str | None = "speaker_id",
) -> dict[str, list[dict]]:
    if not records:
        return {"train": [], "valid": [], "test": []}

    rng = random.Random(seed)
    shuffled = records[:]
    rng.shuffle(shuffled)

    grouped: dict[str, list[dict]] = {}
    for record in shuffled:
        grouped.setdefault(_record_group_key(record, group_key), []).append(record)

    grouped_records = list(grouped.values())
    rng.shuffle(grouped_records)

    total_records = len(records)
    test_target = _target_size(total_records, test_ratio, ensure_one=True)
    valid_target = _target_size(total_records, valid_ratio, ensure_one=True)

    if total_records >= 5 and valid_target == 0:
        valid_target = 1
    if total_records >= 5 and test_target == 0:
        test_target = 1

    while valid_target + test_target >= total_records and (valid_target > 0 or test_target > 0):
        if valid_target >= test_target and valid_target > 0:
            valid_target -= 1
        elif test_target > 0:
            test_target -= 1

    splits = {"train": [], "valid": [], "test": []}
    for group in grouped_records:
        if len(splits["test"]) < test_target:
            splits["test"].extend(group)
        elif len(splits["valid"]) < valid_target:
            splits["valid"].extend(group)
        else:
            splits["train"].extend(group)

    if not splits["train"]:
        if splits["valid"]:
            splits["train"].append(splits["valid"].pop())
        elif splits["test"]:
            splits["train"].append(splits["test"].pop())

    return splits
