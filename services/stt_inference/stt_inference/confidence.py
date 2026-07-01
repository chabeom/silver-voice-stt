from __future__ import annotations

import math
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def logprob_to_confidence(avg_logprob: float | None) -> float:
    if avg_logprob is None:
        return 0.0
    confidence = math.exp(min(0.0, avg_logprob))
    return max(0.0, min(1.0, confidence))


def average_confidence(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class ConfidenceCalibrator:
    """Maps Whisper's raw confidence to an empirically observed success rate."""

    points: list[tuple[float, float]]
    source_path: str | None = None

    @property
    def is_calibrated(self) -> bool:
        return bool(self.points)

    def calibrate(self, raw_confidence: float) -> float:
        raw = _clamp_probability(raw_confidence)
        if not self.points:
            return raw

        points = sorted(self.points)
        if raw <= points[0][0]:
            return _clamp_probability(points[0][1])
        if raw >= points[-1][0]:
            return _clamp_probability(points[-1][1])

        for (left_x, left_y), (right_x, right_y) in zip(points, points[1:]):
            if left_x <= raw <= right_x:
                width = right_x - left_x
                if width <= 0:
                    return _clamp_probability(right_y)
                ratio = (raw - left_x) / width
                return _clamp_probability(left_y + (right_y - left_y) * ratio)
        return raw

    @classmethod
    def from_file(cls, path: str | None) -> "ConfidenceCalibrator":
        if not path:
            return cls(points=[])

        calibration_path = Path(path)
        if not calibration_path.exists():
            return cls(points=[], source_path=str(calibration_path))

        payload: dict[str, Any] = json.loads(calibration_path.read_text(encoding="utf-8"))
        points = [
            (float(point["raw_confidence"]), float(point["calibrated_confidence"]))
            for point in payload.get("points", [])
        ]
        return cls(points=points, source_path=str(calibration_path))
