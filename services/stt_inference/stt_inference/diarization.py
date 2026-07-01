from __future__ import annotations

from functools import lru_cache
from typing import Any


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def assign_speakers_to_segments(
    segments: list[dict[str, Any]],
    speaker_turns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    speaker_order: dict[str, int] = {}
    for turn in sorted(speaker_turns, key=lambda item: float(item["start_sec"])):
        label = str(turn["speaker_label"])
        speaker_order.setdefault(label, len(speaker_order) + 1)

    assigned: list[dict[str, Any]] = []
    for segment in segments:
        start_sec = float(segment["start_sec"])
        end_sec = float(segment["end_sec"])
        duration = max(end_sec - start_sec, 0.001)
        overlap_by_speaker: dict[str, float] = {}
        for turn in speaker_turns:
            label = str(turn["speaker_label"])
            overlap_by_speaker[label] = overlap_by_speaker.get(label, 0.0) + _overlap_seconds(
                start_sec,
                end_sec,
                float(turn["start_sec"]),
                float(turn["end_sec"]),
            )

        if overlap_by_speaker and max(overlap_by_speaker.values()) > 0:
            speaker_label = max(overlap_by_speaker, key=overlap_by_speaker.get)
            speaker_confidence = min(1.0, overlap_by_speaker[speaker_label] / duration)
        else:
            midpoint = (start_sec + end_sec) / 2
            nearest = min(
                speaker_turns,
                key=lambda turn: abs(
                    midpoint - ((float(turn["start_sec"]) + float(turn["end_sec"])) / 2)
                ),
                default=None,
            )
            speaker_label = str(nearest["speaker_label"]) if nearest else "UNKNOWN"
            speaker_confidence = 0.0

        assigned.append(
            {
                **segment,
                "speaker_label": speaker_label,
                "speaker_display_name": (
                    f"화자 {speaker_order[speaker_label]}"
                    if speaker_label in speaker_order
                    else "화자 미확인"
                ),
                "speaker_confidence": speaker_confidence,
            }
        )
    return assigned


def _serialize_output(output: Any) -> list[dict[str, float | str]]:
    diarization = getattr(output, "exclusive_speaker_diarization", None)
    if diarization is None:
        diarization = getattr(output, "speaker_diarization", None)
    if diarization is None:
        diarization = output

    if hasattr(diarization, "itertracks"):
        iterator = ((turn, speaker) for turn, _, speaker in diarization.itertracks(yield_label=True))
    else:
        iterator = iter(diarization)

    return [
        {
            "speaker_label": str(speaker),
            "start_sec": float(turn.start),
            "end_sec": float(turn.end),
        }
        for turn, speaker in iterator
    ]


@lru_cache(maxsize=2)
def _load_pipeline(model_name: str, token: str, device: str):
    import torch
    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(model_name, token=token)
    pipeline.to(torch.device(device))
    return pipeline


def run_speaker_diarization(
    input_path: str,
    *,
    model_name: str,
    token: str | None,
    device: str,
    num_speakers: int | None,
    mock_mode: bool,
    duration: float,
) -> list[dict[str, float | str]]:
    if mock_mode:
        split = max(duration / 2, 0.1)
        return [
            {"speaker_label": "SPEAKER_00", "start_sec": 0.0, "end_sec": split},
            {"speaker_label": "SPEAKER_01", "start_sec": split, "end_sec": max(duration, split)},
        ]

    if not token:
        raise RuntimeError(
            "Speaker diarization requires HF_TOKEN after accepting the pyannote model conditions."
        )

    pipeline = _load_pipeline(model_name, token, device)
    kwargs = {"num_speakers": num_speakers} if num_speakers is not None else {}
    return _serialize_output(pipeline(input_path, **kwargs))
