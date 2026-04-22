from training_pipeline.metrics import compute_error_rates


def test_compute_error_rates():
    metrics = compute_error_rates(["안녕하세요"], ["안녕하세요"])
    assert metrics["wer"] == 0.0
    assert metrics["cer"] == 0.0

