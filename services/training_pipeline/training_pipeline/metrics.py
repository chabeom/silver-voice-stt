from jiwer import cer, wer


def compute_error_rates(references: list[str], predictions: list[str]) -> dict[str, float]:
    return {
        "wer": wer(references, predictions),
        "cer": cer(references, predictions),
    }

