import math


def logprob_to_confidence(avg_logprob: float | None) -> float:
    if avg_logprob is None:
        return 0.0
    confidence = math.exp(min(0.0, avg_logprob))
    return max(0.0, min(1.0, confidence))


def average_confidence(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

