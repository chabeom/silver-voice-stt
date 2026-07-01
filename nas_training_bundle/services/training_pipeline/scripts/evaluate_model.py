import argparse
import json

from training_pipeline.metrics import compute_error_rates


def load_manifest(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-manifest", required=True)
    parser.add_argument("--prediction-manifest", required=True)
    args = parser.parse_args()

    references = load_manifest(args.reference_manifest)
    predictions = load_manifest(args.prediction_manifest)
    metrics = compute_error_rates(
        [item["text"] for item in references],
        [item["text"] for item in predictions],
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

