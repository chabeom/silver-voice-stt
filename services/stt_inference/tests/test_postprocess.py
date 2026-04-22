import wave
from pathlib import Path

from stt_inference.audio import apply_energy_vad
from stt_inference.confidence import logprob_to_confidence
from stt_inference.postprocess import normalize_korean_text


def test_normalize_korean_text():
    text = "2024 년 3 월 1 일 에 연락처는 01012341234 입니다 음 음"
    normalized = normalize_korean_text(text)
    assert "2024년 3월 1일" in normalized
    assert "010-1234-1234" in normalized


def test_logprob_confidence_range():
    confidence = logprob_to_confidence(-0.5)
    assert 0.0 <= confidence <= 1.0


def test_energy_vad_keeps_voiced_frames(tmp_path: Path):
    source_path = tmp_path / "source.wav"
    target_path = tmp_path / "target.wav"

    with wave.open(str(source_path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        silence = (b"\x00\x00" * 1600)
        voiced = (b"\xff\x0f" * 1600)
        writer.writeframes(silence + voiced + silence)

    apply_energy_vad(str(source_path), str(target_path), threshold=100)
    assert target_path.exists()
    assert target_path.stat().st_size > 0

