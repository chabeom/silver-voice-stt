from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Any

from training_pipeline.manifest import summarize_records, train_valid_test_split, write_jsonl


AUDIO_COLUMNS = ("audio_path", "audio", "file", "path", "wav_path")
TEXT_COLUMNS = ("text", "transcript", "corrected_text", "sentence", "utterance")
SPEAKER_COLUMNS = ("speaker_id", "speaker", "speaker_name", "speaker_code")
SAMPLE_ID_COLUMNS = ("sample_id", "id", "record_id", "utterance_id")
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aac", ".wma"}
WHITESPACE_PATTERN = re.compile(r"\s+")
SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _load_metadata_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        text = _read_text(path)
        reader = csv.DictReader(text.splitlines())
        return [dict(row) for row in reader if any((value or "").strip() for value in row.values())]

    if suffix == ".jsonl":
        return [json.loads(line) for line in _read_text(path).splitlines() if line.strip()]

    if suffix == ".json":
        payload = json.loads(_read_text(path))
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("records", "data", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        raise ValueError("JSON metadata must be a list, or an object with records/data/items.")

    raise ValueError("Metadata file must be CSV, JSONL, or JSON.")


def _first_non_empty(row: dict[str, Any], candidates: tuple[str, ...]) -> str | None:
    lowered = {key.lower(): value for key, value in row.items()}
    for candidate in candidates:
        value = lowered.get(candidate)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_text(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text.replace("\ufeff", " ").replace("\u200b", " ")).strip()


def _resolve_audio_path(raw_path: str, metadata_dir: Path, audio_root: Path | None) -> Path | None:
    candidate = Path(raw_path.strip().strip("\"'"))
    if candidate.is_absolute() and candidate.exists():
        return candidate

    search_roots = []
    if audio_root is not None:
        search_roots.append(audio_root)
    search_roots.extend([metadata_dir, Path.cwd()])

    for root in search_roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved

    return None


def _safe_sample_id(value: str) -> str:
    cleaned = SAFE_NAME_PATTERN.sub("_", value.strip())
    return cleaned.strip("._") or uuid.uuid4().hex


def _duration_with_soundfile(audio_path: Path) -> float | None:
    try:
        import soundfile as sf
    except ImportError:
        return None

    try:
        return float(sf.info(str(audio_path)).duration)
    except Exception:
        return None


def _duration_with_wave(audio_path: Path) -> float | None:
    if audio_path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(audio_path), "rb") as handle:
            frame_rate = handle.getframerate()
            if frame_rate <= 0:
                return None
            return float(handle.getnframes() / frame_rate)
    except Exception:
        return None


def _duration_with_ffprobe(audio_path: Path, ffprobe_path: str) -> float | None:
    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def _read_audio_duration(audio_path: Path, ffprobe_path: str) -> float | None:
    return (
        _duration_with_soundfile(audio_path)
        or _duration_with_wave(audio_path)
        or _duration_with_ffprobe(audio_path, ffprobe_path)
    )


def _convert_to_wav(source_path: Path, target_path: Path, ffmpeg_path: str) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_path,
            "-y",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(target_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return target_path


def _build_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metadata_file = Path(args.metadata_file).resolve()
    metadata_dir = metadata_file.parent
    audio_root = Path(args.audio_root).resolve() if args.audio_root else None
    converted_audio_dir = Path(args.converted_audio_dir).resolve() if args.converted_audio_dir else Path(args.output_dir).resolve() / "audio_16k"
    rows = _load_metadata_rows(metadata_file)

    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, row in enumerate(rows):
        raw_audio_path = _first_non_empty(row, AUDIO_COLUMNS)
        raw_text = _first_non_empty(row, TEXT_COLUMNS)
        if not raw_audio_path or not raw_text:
            skipped.append({"row": index + 1, "reason": "missing audio_path or text"})
            continue

        source_audio_path = _resolve_audio_path(raw_audio_path, metadata_dir, audio_root)
        if source_audio_path is None:
            skipped.append({"row": index + 1, "reason": "audio file not found", "audio_path": raw_audio_path})
            continue

        if source_audio_path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
            skipped.append({"row": index + 1, "reason": "unsupported audio suffix", "audio_path": str(source_audio_path)})
            continue

        text = _normalize_text(raw_text)
        if not text:
            skipped.append({"row": index + 1, "reason": "empty normalized text"})
            continue

        raw_sample_id = _first_non_empty(row, SAMPLE_ID_COLUMNS) or source_audio_path.stem
        sample_id = _safe_sample_id(raw_sample_id)
        if sample_id in seen_ids:
            sample_id = f"{sample_id}_{index + 1:06d}"
        seen_ids.add(sample_id)

        audio_path = source_audio_path
        if args.convert_to_wav:
            audio_path = converted_audio_dir / f"{sample_id}.wav"
            if not audio_path.exists() or args.overwrite_converted_audio:
                try:
                    _convert_to_wav(source_audio_path, audio_path, args.ffmpeg_path)
                except subprocess.CalledProcessError as exc:
                    skipped.append(
                        {
                            "row": index + 1,
                            "reason": "ffmpeg conversion failed",
                            "audio_path": str(source_audio_path),
                            "stderr": exc.stderr[-500:] if exc.stderr else "",
                        }
                    )
                    continue

        duration_sec = _read_audio_duration(audio_path, args.ffprobe_path)
        if args.min_duration_seconds is not None and duration_sec is not None and duration_sec < args.min_duration_seconds:
            skipped.append({"row": index + 1, "reason": "too short", "duration_sec": duration_sec})
            continue
        if args.max_duration_seconds is not None and duration_sec is not None and duration_sec > args.max_duration_seconds:
            skipped.append({"row": index + 1, "reason": "too long", "duration_sec": duration_sec})
            continue

        metadata = {
            "metadata_file": str(metadata_file),
            "row_number": index + 1,
            "original_audio_path": str(source_audio_path),
        }
        for key, value in row.items():
            if key not in metadata and value not in (None, ""):
                metadata[key] = value

        records.append(
            {
                "sample_id": sample_id,
                "audio_path": str(audio_path.resolve()),
                "text": text,
                "speaker_id": _first_non_empty(row, SPEAKER_COLUMNS),
                "speaker_type": _first_non_empty(row, ("speaker_type", "age_group")) or args.speaker_type,
                "source": _first_non_empty(row, ("source", "dataset")) or args.source_name,
                "duration_sec": duration_sec,
                "metadata": metadata,
            }
        )

        if args.max_samples is not None and len(records) >= args.max_samples:
            break

    return records, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Build train/valid/test manifests from local STT metadata.")
    parser.add_argument("--metadata-file", required=True, help="CSV/JSONL/JSON with audio_path and text columns.")
    parser.add_argument("--audio-root", help="Base directory used when audio_path values are relative.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--speaker-type", default="elderly")
    parser.add_argument("--source-name", default="local_elderly_speech")
    parser.add_argument("--valid-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--group-key", default="speaker_id")
    parser.add_argument("--min-duration-seconds", type=float, default=0.3)
    parser.add_argument("--max-duration-seconds", type=float, default=30.0)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--convert-to-wav", action="store_true", help="Convert audio to 16kHz mono WAV with ffmpeg.")
    parser.add_argument("--converted-audio-dir")
    parser.add_argument("--overwrite-converted-audio", action="store_true")
    parser.add_argument("--ffmpeg-path", default="ffmpeg")
    parser.add_argument("--ffprobe-path", default="ffprobe")
    args = parser.parse_args()

    records, skipped = _build_records(args)
    splits = train_valid_test_split(
        records,
        seed=args.seed,
        valid_ratio=args.valid_ratio,
        test_ratio=args.test_ratio,
        group_key=args.group_key,
    )

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for split_name, split_records in splits.items():
        write_jsonl(split_records, str(output_dir / f"{split_name}.jsonl"))

    summary = {
        "metadata_file": str(Path(args.metadata_file).resolve()),
        "audio_root": str(Path(args.audio_root).resolve()) if args.audio_root else None,
        "total": summarize_records(records),
        "splits": {split_name: summarize_records(split_records) for split_name, split_records in splits.items()},
        "skipped_count": len(skipped),
        "skipped_examples": skipped[:20],
        "converted_to_wav": bool(args.convert_to_wav),
    }
    (output_dir / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
