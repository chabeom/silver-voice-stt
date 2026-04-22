from __future__ import annotations

import csv
import json
import math
import re
import wave
from pathlib import Path
from typing import Any, Iterable

TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
SPEAKER_MARKER_PATTERN = re.compile(r"^(참석자|화자|speaker)\s*[:：]?\s*\d+\s*$", re.IGNORECASE)
SPEAKER_INLINE_PATTERN = re.compile(r"^(참석자|화자|speaker)\s*[:：]?\s*\d+\s*", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?。！？])\s+")


def build_manifest_record(
    audio_path: str,
    text: str,
    speaker_type: str,
    source: str,
    metadata: dict | None = None,
    *,
    sample_id: str | None = None,
    speaker_id: str | None = None,
    duration_sec: float | None = None,
) -> dict:
    return {
        "sample_id": sample_id,
        "audio_path": audio_path,
        "text": text,
        "speaker_id": speaker_id,
        "speaker_type": speaker_type,
        "source": source,
        "duration_sec": duration_sec,
        "metadata": metadata or {},
    }


def read_text_with_fallback(path: str | Path) -> str:
    target = Path(path)
    raw = target.read_bytes()
    for encoding in TEXT_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def read_json_with_fallback(path: str | Path) -> dict[str, Any]:
    return json.loads(read_text_with_fallback(path))


def normalize_transcript_text(text: str) -> str:
    if not text:
        return ""

    normalized_lines: list[str] = []
    for raw_line in text.replace("\ufeff", " ").replace("\u200b", " ").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if SPEAKER_MARKER_PATTERN.fullmatch(line):
            continue
        line = SPEAKER_INLINE_PATTERN.sub("", line)
        line = WHITESPACE_PATTERN.sub(" ", line).strip(" \"'")
        if line:
            normalized_lines.append(line)
    return " ".join(normalized_lines).strip()


def _iter_turn_texts(turns: Iterable[dict[str, Any]]) -> Iterable[str]:
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        for key in ("question", "answer", "text", "utterance", "sentence"):
            value = turn.get(key)
            if isinstance(value, str):
                normalized = normalize_transcript_text(value)
                if normalized:
                    yield normalized


def extract_aihub_turns(payload: dict[str, Any], raw_text_fallback: str | None = None) -> list[str]:
    qa = payload.get("qa") or payload.get("dialogue") or payload.get("sentences")
    if isinstance(qa, list):
        turns = list(_iter_turn_texts(qa))
        if turns:
            return turns

    transcript = extract_aihub_transcript(payload, raw_text_fallback)
    return [transcript] if transcript else []


def extract_aihub_transcript(payload: dict[str, Any], raw_text_fallback: str | None = None) -> str:
    for key in ("text", "transcription", "utterance", "sentence"):
        value = payload.get(key)
        if isinstance(value, str):
            normalized = normalize_transcript_text(value)
            if normalized:
                return normalized

    qa = payload.get("qa") or payload.get("dialogue") or payload.get("sentences")
    if isinstance(qa, list):
        conversation = " ".join(_iter_turn_texts(qa)).strip()
        if conversation:
            return conversation

    if raw_text_fallback:
        return normalize_transcript_text(raw_text_fallback)

    return ""


def read_audio_duration(audio_path: str | Path) -> float | None:
    try:
        import soundfile as sf
    except ImportError:
        sf = None

    if sf is not None:
        try:
            return float(sf.info(str(audio_path)).duration)
        except RuntimeError:
            pass

    target = Path(audio_path)
    if target.suffix.lower() == ".wav":
        with wave.open(str(target), "rb") as handle:
            frame_count = handle.getnframes()
            frame_rate = handle.getframerate()
            if frame_rate > 0:
                return float(frame_count / frame_rate)
    return None


def export_wav_segment(source_audio_path: str | Path, target_audio_path: str | Path, start_sec: float, end_sec: float) -> None:
    source = Path(source_audio_path)
    target = Path(target_audio_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(source), "rb") as source_handle:
        frame_rate = source_handle.getframerate()
        start_frame = max(0, int(start_sec * frame_rate))
        end_frame = min(source_handle.getnframes(), int(end_sec * frame_rate))
        if end_frame <= start_frame:
            return

        source_handle.setpos(start_frame)
        frames = source_handle.readframes(end_frame - start_frame)

        with wave.open(str(target), "wb") as target_handle:
            target_handle.setnchannels(source_handle.getnchannels())
            target_handle.setsampwidth(source_handle.getsampwidth())
            target_handle.setframerate(frame_rate)
            target_handle.writeframes(frames)


def build_turn_based_segments(turns: list[str], total_duration_sec: float, target_duration_sec: float) -> list[dict[str, Any]]:
    if not turns or total_duration_sec <= 0:
        return []

    expanded_turns: list[str] = []
    for turn in turns:
        sentences = [segment.strip() for segment in SENTENCE_SPLIT_PATTERN.split(turn) if segment.strip()]
        if len(sentences) > 1:
            expanded_turns.extend(sentences)
        else:
            chunk_size = 120
            if len(turn) > chunk_size:
                expanded_turns.extend(
                    turn[index : index + chunk_size].strip()
                    for index in range(0, len(turn), chunk_size)
                    if turn[index : index + chunk_size].strip()
                )
            else:
                expanded_turns.append(turn)

    weighted_turns = [(turn, max(len(turn.replace(" ", "")), 1)) for turn in expanded_turns]
    total_weight = sum(weight for _, weight in weighted_turns)
    if total_weight <= 0:
        return []

    segments: list[dict[str, Any]] = []
    current_texts: list[str] = []
    current_start = 0.0
    current_duration = 0.0
    elapsed = 0.0

    for turn_text, weight in weighted_turns:
        turn_duration = total_duration_sec * (weight / total_weight)
        turn_start = elapsed
        turn_end = elapsed + turn_duration

        if current_texts and current_duration + turn_duration > target_duration_sec:
            segments.append(
                {
                    "text": " ".join(current_texts).strip(),
                    "start_sec": current_start,
                    "end_sec": turn_start,
                }
            )
            current_texts = [turn_text]
            current_start = turn_start
            current_duration = turn_duration
        else:
            if not current_texts:
                current_start = turn_start
            current_texts.append(turn_text)
            current_duration += turn_duration

        elapsed = turn_end

    if current_texts:
        segments.append(
            {
                "text": " ".join(current_texts).strip(),
                "start_sec": current_start,
                "end_sec": total_duration_sec,
            }
        )

    refined_segments: list[dict[str, Any]] = []
    for segment in segments:
        segment_duration = segment["end_sec"] - segment["start_sec"]
        if segment_duration <= target_duration_sec:
            refined_segments.append(segment)
            continue

        part_count = max(2, math.ceil(segment_duration / target_duration_sec))
        words = segment["text"].split()
        if len(words) >= part_count:
            chunk_size = math.ceil(len(words) / part_count)
            text_chunks = [
                " ".join(words[index : index + chunk_size]).strip()
                for index in range(0, len(words), chunk_size)
                if " ".join(words[index : index + chunk_size]).strip()
            ]
        else:
            text = segment["text"]
            char_chunk = math.ceil(len(text) / part_count)
            text_chunks = [
                text[index : index + char_chunk].strip()
                for index in range(0, len(text), char_chunk)
                if text[index : index + char_chunk].strip()
            ]

        if not text_chunks:
            refined_segments.append(segment)
            continue

        chunk_duration = segment_duration / len(text_chunks)
        chunk_start = segment["start_sec"]
        for text_chunk in text_chunks:
            chunk_end = min(segment["end_sec"], chunk_start + chunk_duration)
            refined_segments.append(
                {
                    "text": text_chunk,
                    "start_sec": chunk_start,
                    "end_sec": chunk_end,
                }
            )
            chunk_start = chunk_end

    return [segment for segment in refined_segments if segment["text"] and segment["end_sec"] > segment["start_sec"]]


def resolve_aihub_dataset_roots(dataset_root: str | Path) -> tuple[Path, Path]:
    root = Path(dataset_root)
    direct_candidates = [root]
    direct_candidates.extend(sorted(path for path in root.iterdir() if path.is_dir()))

    for candidate in direct_candidates:
        source_root = candidate / "01.원천데이터"
        label_root = candidate / "02.라벨링데이터"
        if source_root.exists() and label_root.exists():
            return source_root, label_root

    source_dirs = sorted(path for path in root.rglob("01.원천데이터") if path.is_dir())
    label_dirs = sorted(path for path in root.rglob("02.라벨링데이터") if path.is_dir())
    for source_root in source_dirs:
        for label_root in label_dirs:
            if source_root.parent == label_root.parent:
                return source_root, label_root

    raise FileNotFoundError("AI-Hub sample folders '01.원천데이터' and '02.라벨링데이터' were not found")


def _find_audio_file(source_root: Path, relative_label_path: Path) -> Path | None:
    audio_base = source_root / relative_label_path.with_suffix("")
    for suffix in (".wav", ".flac", ".mp3", ".m4a"):
        candidate = audio_base.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return None


def _derive_speaker_id(payload: dict[str, Any]) -> str | None:
    for key in ("speaker_id", "speakerId", "teller_id", "tellerId", "id"):
        value = payload.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value)
    return None


def iter_aihub_sample_records(
    dataset_root: str | Path,
    *,
    speaker_type: str = "elderly_or_disordered",
    source_name: str = "aihub_sample",
    min_duration_seconds: float | None = None,
    max_duration_seconds: float | None = None,
    segment_long_audio: bool = False,
    segment_audio_dir: str | Path | None = None,
    target_segment_seconds: float | None = None,
) -> Iterable[dict]:
    source_root, label_root = resolve_aihub_dataset_roots(dataset_root)

    for label_path in sorted(label_root.rglob("*.json")):
        relative_path = label_path.relative_to(label_root)
        audio_path = _find_audio_file(source_root, relative_path)
        if audio_path is None:
            continue

        transcript_path = (source_root / relative_path).with_suffix(".txt")
        raw_transcript = read_text_with_fallback(transcript_path) if transcript_path.exists() else None
        payload = read_json_with_fallback(label_path)
        transcript = extract_aihub_transcript(payload, raw_transcript)
        turns = extract_aihub_turns(payload, raw_transcript)
        if not transcript:
            continue

        duration_sec = read_audio_duration(audio_path)
        if min_duration_seconds is not None and duration_sec is not None and duration_sec < min_duration_seconds:
            continue

        sample_id = str(payload.get("jsonId") or audio_path.stem)
        if (
            segment_long_audio
            and segment_audio_dir is not None
            and duration_sec is not None
            and max_duration_seconds is not None
            and duration_sec > max_duration_seconds
            and audio_path.suffix.lower() == ".wav"
        ):
            segments = build_turn_based_segments(turns, duration_sec, target_segment_seconds or max_duration_seconds)
            for segment_index, segment in enumerate(segments):
                segment_duration = segment["end_sec"] - segment["start_sec"]
                if min_duration_seconds is not None and segment_duration < min_duration_seconds:
                    continue
                if max_duration_seconds is not None and segment_duration > max_duration_seconds * 1.2:
                    continue

                segment_path = Path(segment_audio_dir) / relative_path.parent / f"{audio_path.stem}__seg_{segment_index:03d}.wav"
                export_wav_segment(audio_path, segment_path, segment["start_sec"], segment["end_sec"])
                if not segment_path.exists():
                    continue

                metadata = {
                    "category": relative_path.parts[0] if relative_path.parts else "",
                    "relative_path": str(relative_path),
                    "label_path": str(label_path),
                    "transcript_path": str(transcript_path) if transcript_path.exists() else None,
                    "keyword": payload.get("keyword"),
                    "json_id": payload.get("jsonId"),
                    "audio_time": payload.get("audioTime"),
                    "qa_count": len(payload.get("qa", [])) if isinstance(payload.get("qa"), list) else None,
                    "original_audio_path": str(audio_path),
                    "segment_index": segment_index,
                    "segment_start_sec": round(segment["start_sec"], 3),
                    "segment_end_sec": round(segment["end_sec"], 3),
                }

                yield build_manifest_record(
                    audio_path=str(segment_path),
                    text=segment["text"],
                    speaker_type=speaker_type,
                    source=source_name,
                    metadata=metadata,
                    sample_id=f"{sample_id}-seg-{segment_index:03d}",
                    speaker_id=_derive_speaker_id(payload),
                    duration_sec=segment_duration,
                )
            continue

        if max_duration_seconds is not None and duration_sec is not None and duration_sec > max_duration_seconds:
            continue

        metadata = {
            "category": relative_path.parts[0] if relative_path.parts else "",
            "relative_path": str(relative_path),
            "label_path": str(label_path),
            "transcript_path": str(transcript_path) if transcript_path.exists() else None,
            "keyword": payload.get("keyword"),
            "json_id": payload.get("jsonId"),
            "audio_time": payload.get("audioTime"),
            "qa_count": len(payload.get("qa", [])) if isinstance(payload.get("qa"), list) else None,
        }

        yield build_manifest_record(
            audio_path=str(audio_path),
            text=transcript,
            speaker_type=speaker_type,
            source=source_name,
            metadata=metadata,
            sample_id=sample_id,
            speaker_id=_derive_speaker_id(payload),
            duration_sec=duration_sec,
        )


def load_corrections_export(csv_or_jsonl_path: str) -> list[dict]:
    path = Path(csv_or_jsonl_path)
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in read_text_with_fallback(path).splitlines() if line.strip()]

    if path.suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]

    raise ValueError("Only JSONL and CSV correction exports are supported")
