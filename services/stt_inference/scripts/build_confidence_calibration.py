import argparse
import json
from pathlib import Path
from typing import Any


def normalize_text(text: str) -> str:
    return "".join(text.split())


def edit_distance(reference: str, prediction: str) -> int:
    previous = list(range(len(prediction) + 1))
    for reference_index, reference_char in enumerate(reference, start=1):
        current = [reference_index]
        for prediction_index, prediction_char in enumerate(prediction, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[prediction_index] + 1,
                    previous[prediction_index - 1] + (reference_char != prediction_char),
                )
            )
        previous = current
    return previous[-1]


def calculate_cer(reference_text: str, predicted_text: str) -> float:
    reference = normalize_text(reference_text)
    prediction = normalize_text(predicted_text)
    if not reference:
        return 0.0 if not prediction else 1.0
    return edit_distance(reference, prediction) / len(reference)


def load_records(path: Path, success_cer_threshold: float) -> list[tuple[float, bool]]:
    records: list[tuple[float, bool]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        item: dict[str, Any] = json.loads(line)
        raw_confidence = float(item["raw_confidence"])
        cer = item.get("cer")
        if cer is None:
            if "reference_text" not in item or "predicted_text" not in item:
                raise ValueError(
                    f"Line {line_number} needs cer or both reference_text and predicted_text."
                )
            cer = calculate_cer(str(item["reference_text"]), str(item["predicted_text"]))
        records.append((max(0.0, min(1.0, raw_confidence)), float(cer) <= success_cer_threshold))
    if not records:
        raise ValueError("No calibration records were found.")
    return records


def isotonic_non_decreasing(values: list[float], weights: list[float]) -> list[float]:
    blocks: list[dict[str, float | int]] = []
    for index, (value, weight) in enumerate(zip(values, weights)):
        blocks.append({"start": index, "end": index, "value": value, "weight": weight})
        while len(blocks) >= 2 and float(blocks[-2]["value"]) > float(blocks[-1]["value"]):
            right = blocks.pop()
            left = blocks.pop()
            combined_weight = float(left["weight"]) + float(right["weight"])
            combined_value = (
                float(left["value"]) * float(left["weight"])
                + float(right["value"]) * float(right["weight"])
            ) / combined_weight
            blocks.append(
                {
                    "start": int(left["start"]),
                    "end": int(right["end"]),
                    "value": combined_value,
                    "weight": combined_weight,
                }
            )

    result = [0.0] * len(values)
    for block in blocks:
        for index in range(int(block["start"]), int(block["end"]) + 1):
            result[index] = float(block["value"])
    return result


def build_calibration(
    records: list[tuple[float, bool]],
    *,
    bin_count: int,
    success_cer_threshold: float,
) -> dict[str, Any]:
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(bin_count)]
    for raw_confidence, success in records:
        bin_index = min(int(raw_confidence * bin_count), bin_count - 1)
        bins[bin_index].append((raw_confidence, success))

    populated = [items for items in bins if items]
    raw_points = [sum(raw for raw, _ in items) / len(items) for items in populated]
    empirical_rates = [
        (sum(1 for _, success in items if success) + 1) / (len(items) + 2)
        for items in populated
    ]
    weights = [float(len(items) + 2) for items in populated]
    calibrated_rates = isotonic_non_decreasing(empirical_rates, weights)

    points = [
        {
            "raw_confidence": raw,
            "calibrated_confidence": calibrated,
            "sample_count": len(items),
            "success_count": sum(1 for _, success in items if success),
        }
        for raw, calibrated, items in zip(raw_points, calibrated_rates, populated)
    ]
    return {
        "version": 1,
        "method": "binned_empirical_isotonic",
        "success_definition": f"CER <= {success_cer_threshold}",
        "success_cer_threshold": success_cer_threshold,
        "sample_count": len(records),
        "points": points,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a confidence calibration map from labeled STT evaluation JSONL."
    )
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--success-cer-threshold", type=float, default=0.1)
    parser.add_argument("--bin-count", type=int, default=10)
    args = parser.parse_args()

    if args.bin_count < 2:
        raise ValueError("--bin-count must be at least 2.")

    records = load_records(Path(args.input_jsonl), args.success_cer_threshold)
    calibration = build_calibration(
        records,
        bin_count=args.bin_count,
        success_cer_threshold=args.success_cer_threshold,
    )
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(calibration, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
