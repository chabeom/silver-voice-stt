from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from training_pipeline.dataset import (
    _build_audio_index,
    _find_audio_file,
    _derive_teller_profile,
    build_manifest_record,
    export_wav_segment,
    normalize_transcript_text,
    read_audio_duration,
    read_json_with_fallback,
    resolve_aihub_dataset_roots,
)
from training_pipeline.manifest import summarize_records, train_valid_test_split, write_jsonl


HANGUL_BASE = 0xAC00
HANGUL_END = 0xD7A3
HANGUL_INITIAL = [
    "g",
    "kk",
    "n",
    "d",
    "tt",
    "r",
    "m",
    "b",
    "pp",
    "s",
    "ss",
    "",
    "j",
    "jj",
    "ch",
    "k",
    "t",
    "p",
    "h",
]
HANGUL_MEDIAL = [
    "a",
    "ae",
    "ya",
    "yae",
    "eo",
    "e",
    "yeo",
    "ye",
    "o",
    "wa",
    "wae",
    "oe",
    "yo",
    "u",
    "wo",
    "we",
    "wi",
    "yu",
    "eu",
    "ui",
    "i",
]
HANGUL_FINAL = [
    "",
    "k",
    "k",
    "ks",
    "n",
    "nj",
    "nh",
    "t",
    "l",
    "lk",
    "lm",
    "lb",
    "ls",
    "lt",
    "lp",
    "lh",
    "m",
    "p",
    "ps",
    "t",
    "t",
    "ng",
    "t",
    "t",
    "k",
    "t",
    "p",
    "h",
]


@dataclass
class Turn:
    role: str
    text: str
    align_text: str
    start_index: int
    end_index: int


def label_match_keys(
    *,
    label_path: str | None = None,
    relative_label_path: str | None = None,
    json_id: str | int | None = None,
) -> set[str]:
    keys: set[str] = set()
    for raw_path in (label_path, relative_label_path):
        if not raw_path:
            continue
        path_text = str(raw_path).replace("\\", "/")
        keys.add(f"path:{path_text}")
        keys.add(f"path:{path_text.lstrip('./')}")
        path = Path(raw_path)
        if path.name:
            keys.add(f"name:{path.name}")
        if path.stem:
            keys.add(f"stem:{path.stem}")
        keys.add(f"resolved:{path.resolve(strict=False)}")
    if json_id is not None and str(json_id).strip():
        keys.add(f"json_id:{json_id}")
    return keys


def load_allowed_validation_keys(
    report_path: str | None,
    *,
    passed_only: bool,
    max_cer: float | None,
    max_wer: float | None,
) -> tuple[set[str], int] | None:
    if not report_path:
        return None

    allowed: set[str] = set()
    allowed_rows = 0
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
            allowed_rows += 1
            allowed.update(
                label_match_keys(
                    label_path=row.get("label_path"),
                    relative_label_path=row.get("relative_label_path"),
                    json_id=row.get("json_id"),
                )
            )
    return allowed, allowed_rows


def record_allowed(label_path: Path, label_root: Path, payload: dict[str, Any], allowed: tuple[set[str], int] | None) -> bool:
    if allowed is None:
        return True
    allowed_keys, _allowed_rows = allowed
    relative_path = label_path.relative_to(label_root)
    keys = label_match_keys(
        label_path=str(label_path),
        relative_label_path=str(relative_path),
        json_id=payload.get("jsonId"),
    )
    return bool(keys & allowed_keys)


def build_qa_turns(payload: dict[str, Any]) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    qa = payload.get("qa")
    if not isinstance(qa, list):
        return turns

    for item in qa:
        if not isinstance(item, dict):
            continue
        question = normalize_transcript_text(str(item.get("question") or ""))
        answer = normalize_transcript_text(str(item.get("answer") or ""))
        if question:
            turns.append({"role": "question", "text": question})
        if answer:
            turns.append({"role": "answer", "text": answer})
    return turns


def run_uroman(text: str, *, uroman_path: str | None) -> str:
    if not text:
        return ""

    command: list[str] | None = None
    if uroman_path:
        path = Path(uroman_path)
        if path.suffix == ".pl":
            command = ["perl", str(path)]
        else:
            command = [str(path)]
    elif shutil.which("uroman"):
        command = ["uroman"]

    if command is None:
        return text

    completed = subprocess.run(
        command,
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return text
    return completed.stdout.strip() or text


def romanize_hangul_fallback(text: str) -> str:
    pieces: list[str] = []
    for character in text:
        code = ord(character)
        if HANGUL_BASE <= code <= HANGUL_END:
            syllable_index = code - HANGUL_BASE
            initial_index = syllable_index // 588
            medial_index = (syllable_index % 588) // 28
            final_index = syllable_index % 28
            pieces.append(
                HANGUL_INITIAL[initial_index]
                + HANGUL_MEDIAL[medial_index]
                + HANGUL_FINAL[final_index]
            )
        else:
            pieces.append(character)
    return "".join(pieces)


def normalize_for_alignment(text: str, dictionary: dict[str, int], *, uroman_path: str | None) -> str:
    normalized = run_uroman(normalize_transcript_text(text), uroman_path=uroman_path)
    normalized = romanize_hangul_fallback(normalized).lower()
    output: list[str] = []
    for character in normalized:
        if character.isspace():
            continue
        if character in dictionary:
            output.append(character)
    return "".join(output)


def build_turn_alignment_texts(
    raw_turns: list[dict[str, str]],
    dictionary: dict[str, int],
    *,
    uroman_path: str | None,
) -> tuple[list[Turn], str]:
    turns: list[Turn] = []
    full_text_parts: list[str] = []
    cursor = 0
    for raw_turn in raw_turns:
        align_text = normalize_for_alignment(raw_turn["text"], dictionary, uroman_path=uroman_path)
        if not align_text:
            continue
        start_index = cursor
        end_index = cursor + len(align_text)
        turns.append(
            Turn(
                role=raw_turn["role"],
                text=raw_turn["text"],
                align_text=align_text,
                start_index=start_index,
                end_index=end_index,
            )
        )
        full_text_parts.append(align_text)
        cursor = end_index
    return turns, "".join(full_text_parts)


def ctc_forced_align(emission: Any, tokens: list[int], blank_id: int = 0) -> list[int]:
    import torch

    if not tokens:
        return []

    log_probs = emission.log_softmax(dim=-1).cpu()
    time_steps = log_probs.size(0)
    token_count = len(tokens)
    trellis = torch.full((time_steps + 1, token_count + 1), -float("inf"))
    trellis[0, 0] = 0.0
    trellis[1:, 0] = torch.cumsum(log_probs[:, blank_id], dim=0)

    target = torch.tensor(tokens, dtype=torch.long)
    for t in range(time_steps):
        stay = trellis[t, 1:] + log_probs[t, blank_id]
        change = trellis[t, :-1] + log_probs[t, target]
        trellis[t + 1, 1:] = torch.maximum(stay, change)

    token_frames = [0] * token_count
    j = token_count
    t = int(torch.argmax(trellis[:, j]).item())
    t = max(t, 1)

    while j > 0 and t > 0:
        token_id = tokens[j - 1]
        stayed = trellis[t - 1, j] + log_probs[t - 1, blank_id]
        changed = trellis[t - 1, j - 1] + log_probs[t - 1, token_id]
        if changed > stayed:
            token_frames[j - 1] = t - 1
            j -= 1
        t -= 1

    if j > 0:
        raise RuntimeError("forced alignment backtracking failed")

    return token_frames


def load_mms_fa_model(device: str) -> tuple[Any, dict[str, int], int, int]:
    import torchaudio

    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model().to(device)
    model.eval()
    labels = bundle.get_labels()
    dictionary = {label.lower(): index for index, label in enumerate(labels)}
    sample_rate = int(bundle.sample_rate)
    blank_id = 0
    return model, dictionary, sample_rate, blank_id


def compute_char_times(
    audio_path: Path,
    transcript: str,
    *,
    model: Any,
    dictionary: dict[str, int],
    sample_rate: int,
    blank_id: int,
    device: str,
) -> list[tuple[float, float]]:
    import soundfile as sf
    import torch
    import torchaudio

    audio_array, source_sample_rate = sf.read(str(audio_path), always_2d=True, dtype="float32")
    waveform = torch.from_numpy(audio_array).transpose(0, 1).contiguous()
    if waveform.size(0) > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    if source_sample_rate != sample_rate:
        waveform = torchaudio.functional.resample(waveform, source_sample_rate, sample_rate)

    tokens = [dictionary[character] for character in transcript]
    with torch.inference_mode():
        emission, _ = model(waveform.to(device))
        emission = emission[0]

    token_frames = ctc_forced_align(emission, tokens, blank_id=blank_id)
    duration_sec = float(waveform.size(1) / sample_rate)
    frame_count = emission.size(0)
    seconds_per_frame = duration_sec / max(frame_count, 1)

    char_times: list[tuple[float, float]] = []
    for frame_index in token_frames:
        start = max(0.0, frame_index * seconds_per_frame)
        end = min(duration_sec, (frame_index + 1) * seconds_per_frame)
        char_times.append((start, end))
    return char_times


def split_text_by_char_count(text: str, max_chars: int) -> list[tuple[int, int, str]]:
    if max_chars <= 0 or len(text) <= max_chars:
        return [(0, len(text), text)]

    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            split_at = max(text.rfind(".", start, end), text.rfind("?", start, end), text.rfind("!", start, end), text.rfind(" ", start, end))
            if split_at > start + max_chars // 2:
                end = split_at + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append((start, end, chunk))
        start = end
    return chunks


def turn_time_range(turn: Turn, char_times: list[tuple[float, float]], *, padding_sec: float, audio_duration: float | None) -> tuple[float, float]:
    start = char_times[turn.start_index][0]
    end = char_times[turn.end_index - 1][1]
    start = max(0.0, start - padding_sec)
    if audio_duration is not None:
        end = min(audio_duration, end + padding_sec)
    else:
        end += padding_sec
    return start, end


def main() -> None:
    parser = argparse.ArgumentParser(description="Create answer-only AI-Hub manifests using forced alignment timestamps.")
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--validation-report")
    parser.add_argument("--validation-passed-only", action="store_true")
    parser.add_argument("--max-validation-cer", type=float)
    parser.add_argument("--max-validation-wer", type=float)
    parser.add_argument("--target-role", choices=["answer", "question", "both"], default="answer")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--uroman-path")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-segment-seconds", type=float, default=0.5)
    parser.add_argument("--max-segment-seconds", type=float, default=30.0)
    parser.add_argument("--max-text-chars", type=int, default=220)
    parser.add_argument("--padding-seconds", type=float, default=0.12)
    parser.add_argument("--valid-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source_root, label_root = resolve_aihub_dataset_roots(args.dataset_root)
    audio_index = _build_audio_index(source_root)
    allowed = load_allowed_validation_keys(
        args.validation_report,
        passed_only=args.validation_passed_only,
        max_cer=args.max_validation_cer,
        max_wer=args.max_validation_wer,
    )

    model, dictionary, sample_rate, blank_id = load_mms_fa_model(args.device)
    output_dir = Path(args.output_dir)
    clips_dir = output_dir / "clips"
    alignments_dir = output_dir / "alignments"
    clips_dir.mkdir(parents=True, exist_ok=True)
    alignments_dir.mkdir(parents=True, exist_ok=True)

    label_paths = sorted(label_root.rglob("*.json"))
    if args.limit is not None:
        label_paths = label_paths[: args.limit]

    records: list[dict] = []
    alignment_rows: list[dict[str, Any]] = []
    skipped: dict[str, int] = {
        "validation_filter": 0,
        "audio_not_found": 0,
        "empty_turns": 0,
        "empty_alignment_text": 0,
        "alignment_failed": 0,
        "segment_too_short": 0,
        "segment_too_long": 0,
        "clip_export_failed": 0,
    }

    for index, label_path in enumerate(label_paths, start=1):
        relative_path = label_path.relative_to(label_root)
        payload = read_json_with_fallback(label_path)
        if not record_allowed(label_path, label_root, payload, allowed):
            skipped["validation_filter"] += 1
            continue

        audio_path = _find_audio_file(source_root, relative_path, payload, audio_index)
        if audio_path is None:
            skipped["audio_not_found"] += 1
            continue

        raw_turns = build_qa_turns(payload)
        if not raw_turns:
            skipped["empty_turns"] += 1
            continue

        turns, alignment_text = build_turn_alignment_texts(raw_turns, dictionary, uroman_path=args.uroman_path)
        if not alignment_text:
            skipped["empty_alignment_text"] += 1
            continue

        audio_duration = read_audio_duration(audio_path)
        try:
            char_times = compute_char_times(
                audio_path,
                alignment_text,
                model=model,
                dictionary=dictionary,
                sample_rate=sample_rate,
                blank_id=blank_id,
                device=args.device,
            )
        except Exception as exc:
            skipped["alignment_failed"] += 1
            alignment_rows.append(
                {
                    "status": "failed",
                    "reason": str(exc),
                    "label_path": str(label_path),
                    "relative_label_path": str(relative_path),
                    "audio_path": str(audio_path),
                }
            )
            print(f"[{index}/{len(label_paths)}] alignment failed: {exc} {label_path.name}", flush=True)
            continue

        sample_id = str(payload.get("jsonId") or audio_path.stem)
        teller_profile = _derive_teller_profile(payload)
        file_records = 0
        aligned_turns: list[dict[str, Any]] = []
        for turn_index, turn in enumerate(turns):
            if args.target_role != "both" and turn.role != args.target_role:
                continue

            turn_start, turn_end = turn_time_range(turn, char_times, padding_sec=args.padding_seconds, audio_duration=audio_duration)
            turn_duration = turn_end - turn_start
            text_chunks = split_text_by_char_count(turn.text, args.max_text_chars)
            if len(text_chunks) > 1:
                aligned_length = max(turn.end_index - turn.start_index, 1)
            else:
                aligned_length = 1

            for chunk_index, (text_start, text_end, chunk_text) in enumerate(text_chunks):
                if len(text_chunks) > 1:
                    ratio_start = text_start / max(len(turn.text), 1)
                    ratio_end = text_end / max(len(turn.text), 1)
                    chunk_start = turn_start + turn_duration * ratio_start
                    chunk_end = turn_start + turn_duration * ratio_end
                else:
                    chunk_start = turn_start
                    chunk_end = turn_end

                chunk_duration = chunk_end - chunk_start
                if chunk_duration < args.min_segment_seconds:
                    skipped["segment_too_short"] += 1
                    continue
                if args.max_segment_seconds > 0 and chunk_duration > args.max_segment_seconds * 1.2:
                    skipped["segment_too_long"] += 1
                    continue

                clip_path = clips_dir / relative_path.parent / f"{audio_path.stem}__{turn.role}_{turn_index:03d}_{chunk_index:02d}.wav"
                export_wav_segment(audio_path, clip_path, chunk_start, chunk_end)
                if not clip_path.exists():
                    skipped["clip_export_failed"] += 1
                    continue

                metadata = {
                    "category": relative_path.parts[0] if relative_path.parts else "",
                    "relative_path": str(relative_path),
                    "label_path": str(label_path),
                    "keyword": payload.get("keyword"),
                    "json_id": payload.get("jsonId"),
                    "audio_time": payload.get("audioTime"),
                    "qa_count": len(payload.get("qa", [])) if isinstance(payload.get("qa"), list) else None,
                    "teller": teller_profile["teller"],
                    "original_audio_path": str(audio_path),
                    "alignment_backend": "torchaudio.mms_fa",
                    "turn_role": turn.role,
                    "turn_index": turn_index,
                    "chunk_index": chunk_index,
                    "segment_start_sec": round(chunk_start, 3),
                    "segment_end_sec": round(chunk_end, 3),
                }
                records.append(
                    build_manifest_record(
                        audio_path=str(clip_path),
                        text=chunk_text,
                        speaker_type="elderly_or_disordered" if turn.role == "answer" else "interviewer",
                        source="aihub_forced_aligned",
                        metadata=metadata,
                        sample_id=f"{sample_id}-{turn.role}-{turn_index:03d}-{chunk_index:02d}",
                        speaker_id=teller_profile["speaker_id"],
                        duration_sec=chunk_duration,
                        age=teller_profile["age"],
                        age_group=teller_profile["age_group"],
                        gender=teller_profile["gender"],
                    )
                )
                file_records += 1

            aligned_turns.append(
                {
                    "role": turn.role,
                    "text": turn.text,
                    "start_sec": round(turn_start, 3),
                    "end_sec": round(turn_end, 3),
                    "align_char_count": len(turn.align_text),
                }
            )

        alignment_row = {
            "status": "processed",
            "label_path": str(label_path),
            "relative_label_path": str(relative_path),
            "audio_path": str(audio_path),
            "sample_id": sample_id,
            "audio_duration_sec": audio_duration,
            "created_records": file_records,
            "turns": aligned_turns,
        }
        alignment_rows.append(alignment_row)
        print(f"[{index}/{len(label_paths)}] records={file_records} {label_path.name}", flush=True)

    splits = train_valid_test_split(records, seed=args.seed, valid_ratio=args.valid_ratio, test_ratio=args.test_ratio)
    for split_name, split_records in splits.items():
        write_jsonl(split_records, str(output_dir / f"{split_name}.jsonl"))

    alignment_report_path = alignments_dir / "alignment_report.jsonl"
    alignment_report_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in alignment_rows),
        encoding="utf-8",
    )
    summary = {
        "dataset_root": str(Path(args.dataset_root)),
        "resolved_source_root": str(source_root),
        "resolved_label_root": str(label_root),
        "target_role": args.target_role,
        "alignment_backend": "torchaudio.mms_fa",
        "allowed_label_count": allowed[1] if allowed is not None else None,
        "total": summarize_records(records),
        "splits": {split_name: summarize_records(split_records) for split_name, split_records in splits.items()},
        "skipped": skipped,
        "max_text_chars": args.max_text_chars,
        "min_segment_seconds": args.min_segment_seconds,
        "max_segment_seconds": args.max_segment_seconds,
        "padding_seconds": args.padding_seconds,
        "alignment_report": str(alignment_report_path),
    }
    (output_dir / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
