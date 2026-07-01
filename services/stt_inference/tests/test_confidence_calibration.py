import json
from pathlib import Path

from stt_inference.confidence import ConfidenceCalibrator


def test_calibrator_uses_raw_confidence_when_no_map_exists():
    calibrator = ConfidenceCalibrator.from_file(None)

    assert calibrator.is_calibrated is False
    assert calibrator.calibrate(0.72) == 0.72


def test_calibrator_interpolates_empirical_probability(tmp_path: Path):
    path = tmp_path / "calibration.json"
    path.write_text(
        json.dumps(
            {
                "points": [
                    {"raw_confidence": 0.2, "calibrated_confidence": 0.1},
                    {"raw_confidence": 0.8, "calibrated_confidence": 0.7},
                ]
            }
        ),
        encoding="utf-8",
    )

    calibrator = ConfidenceCalibrator.from_file(str(path))

    assert calibrator.is_calibrated is True
    assert abs(calibrator.calibrate(0.5) - 0.4) < 1e-9
    assert calibrator.calibrate(0.0) == 0.1
    assert calibrator.calibrate(1.0) == 0.7
