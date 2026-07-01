from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HISTORY_COLUMNS = [
    "recorded_at",
    "run_name",
    "status",
    "device",
    "model_name_or_path",
    "output_dir",
    "resume_from_checkpoint",
    "train_strategy",
    "epochs",
    "learning_rate",
    "train_samples",
    "valid_samples",
    "test_samples",
    "train_runtime",
    "train_loss",
    "eval_loss",
    "eval_wer",
    "eval_cer",
    "test_loss",
    "test_wer",
    "test_cer",
    "trainable_params",
    "total_params",
]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(metrics: dict[str, Any], key: str) -> Any:
    value = metrics.get(key)
    return value if isinstance(value, (int, float, str)) else ""


def _build_record(result: dict[str, Any], run_name: str | None, recorded_at: str) -> dict[str, Any]:
    config = result.get("config") or {}
    eval_metrics = result.get("eval_metrics") or {}
    test_metrics = result.get("test_metrics") or {}
    output_dir = config.get("output_dir") or ""

    return {
        "recorded_at": recorded_at,
        "run_name": run_name or Path(output_dir).name or "unnamed-run",
        "status": result.get("status", ""),
        "device": result.get("device", ""),
        "model_name_or_path": config.get("model_name_or_path", ""),
        "output_dir": output_dir,
        "resume_from_checkpoint": config.get("resume_from_checkpoint") or "",
        "train_strategy": config.get("train_strategy", ""),
        "epochs": config.get("num_train_epochs", ""),
        "learning_rate": config.get("learning_rate", ""),
        "train_samples": result.get("train_samples", ""),
        "valid_samples": result.get("valid_samples", ""),
        "test_samples": result.get("test_samples", ""),
        "train_runtime": result.get("train_runtime", ""),
        "train_loss": result.get("train_loss", ""),
        "eval_loss": _metric(eval_metrics, "eval_loss"),
        "eval_wer": _metric(eval_metrics, "eval_wer"),
        "eval_cer": _metric(eval_metrics, "eval_cer"),
        "test_loss": _metric(test_metrics, "test_loss"),
        "test_wer": _metric(test_metrics, "test_wer"),
        "test_cer": _metric(test_metrics, "test_cer"),
        "trainable_params": result.get("trainable_params", ""),
        "total_params": result.get("total_params", ""),
    }


def _append_csv(history_csv: Path, record: dict[str, Any]) -> None:
    history_csv.parent.mkdir(parents=True, exist_ok=True)
    file_exists = history_csv.exists() and history_csv.stat().st_size > 0
    with history_csv.open("a", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)


def _append_jsonl(history_jsonl: Path, record: dict[str, Any], raw_result: dict[str, Any]) -> None:
    history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    payload = {"summary": record, "result": raw_result}
    with history_jsonl.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a Whisper training result to history files.")
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--history-csv", default="models/training_history.csv")
    parser.add_argument("--history-jsonl", default="models/training_history.jsonl")
    parser.add_argument("--run-name")
    args = parser.parse_args()

    result_file = Path(args.result_file).resolve()
    result = _load_json(result_file)
    recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record = _build_record(result, args.run_name, recorded_at)

    _append_csv(Path(args.history_csv), record)
    _append_jsonl(Path(args.history_jsonl), record, result)

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
