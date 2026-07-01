from __future__ import annotations

from pathlib import Path
from typing import Any


def merge_speaker_turns(
    turns: list[dict[str, Any]],
    *,
    speaker: str,
    merge_gap_seconds: float = 0.35,
    min_turn_seconds: float = 0.3,
) -> list[dict[str, float | str]]:
    selected = sorted(
        (
            {
                "speaker": str(turn["speaker"]),
                "start_sec": float(turn["start_sec"]),
                "end_sec": float(turn["end_sec"]),
            }
            for turn in turns
            if str(turn["speaker"]) == speaker
            and float(turn["end_sec"]) - float(turn["start_sec"]) >= min_turn_seconds
        ),
        key=lambda item: float(item["start_sec"]),
    )

    merged: list[dict[str, float | str]] = []
    for turn in selected:
        if merged and float(turn["start_sec"]) - float(merged[-1]["end_sec"]) <= merge_gap_seconds:
            merged[-1]["end_sec"] = max(float(merged[-1]["end_sec"]), float(turn["end_sec"]))
            continue
        merged.append(turn)
    return merged


def choose_longest_speaker(turns: list[dict[str, Any]]) -> str:
    durations: dict[str, float] = {}
    for turn in turns:
        speaker = str(turn["speaker"])
        duration = max(0.0, float(turn["end_sec"]) - float(turn["start_sec"]))
        durations[speaker] = durations.get(speaker, 0.0) + duration
    if not durations:
        raise ValueError("No speaker turns were found.")
    return max(durations, key=durations.get)


def chunk_turns(
    turns: list[dict[str, float | str]],
    *,
    max_chunk_seconds: float,
) -> list[list[dict[str, float | str]]]:
    expanded: list[dict[str, float | str]] = []
    for turn in turns:
        start = float(turn["start_sec"])
        end = float(turn["end_sec"])
        while end - start > max_chunk_seconds:
            expanded.append({**turn, "start_sec": start, "end_sec": start + max_chunk_seconds})
            start += max_chunk_seconds
        if end > start:
            expanded.append({**turn, "start_sec": start, "end_sec": end})

    chunks: list[list[dict[str, float | str]]] = []
    current: list[dict[str, float | str]] = []
    current_duration = 0.0
    for turn in expanded:
        duration = float(turn["end_sec"]) - float(turn["start_sec"])
        if current and current_duration + duration > max_chunk_seconds:
            chunks.append(current)
            current = []
            current_duration = 0.0
        current.append(turn)
        current_duration += duration
    if current:
        chunks.append(current)
    return chunks


def split_text_by_weights(text: str, weights: list[float]) -> list[str]:
    words = text.split()
    if not weights:
        return []
    if not words:
        return [""] * len(weights)

    safe_weights = [max(float(weight), 0.0) for weight in weights]
    total_weight = sum(safe_weights) or float(len(safe_weights))
    chunks: list[str] = []
    cursor = 0
    remaining_words = len(words)

    for index, weight in enumerate(safe_weights):
        remaining_chunks = len(safe_weights) - index
        if remaining_chunks == 1:
            take = remaining_words
        else:
            target = round(len(words) * (weight / total_weight))
            take = max(1, min(target, remaining_words - (remaining_chunks - 1)))
        chunks.append(" ".join(words[cursor : cursor + take]))
        cursor += take
        remaining_words -= take
    return chunks


def write_concatenated_wav(
    source_audio_path: str | Path,
    target_audio_path: str | Path,
    turns: list[dict[str, float | str]],
    *,
    target_sample_rate: int = 16000,
) -> float:
    import librosa
    import numpy as np
    import soundfile as sf

    audio, sample_rate = sf.read(str(source_audio_path), always_2d=False)
    if getattr(audio, "ndim", 1) > 1:
        audio = np.mean(audio, axis=1)
    audio = audio.astype(np.float32)
    if sample_rate != target_sample_rate:
        audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sample_rate)
        sample_rate = target_sample_rate

    pieces = []
    for turn in turns:
        start_sample = max(0, int(float(turn["start_sec"]) * sample_rate))
        end_sample = min(len(audio), int(float(turn["end_sec"]) * sample_rate))
        if end_sample > start_sample:
            pieces.append(audio[start_sample:end_sample])

    target = Path(target_audio_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    combined = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
    sf.write(str(target), combined, sample_rate)
    return float(len(combined) / sample_rate)
