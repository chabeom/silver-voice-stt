import audioop
import subprocess
import wave
from pathlib import Path


def convert_to_mono_16k(input_path: str, output_path: str) -> str:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        output_path,
    ]
    subprocess.run(command, check=True, capture_output=True)
    return output_path


def apply_energy_vad(input_wav_path: str, output_wav_path: str, threshold: int = 350, frame_ms: int = 30) -> str:
    with wave.open(input_wav_path, "rb") as reader:
        params = reader.getparams()
        sample_rate = reader.getframerate()
        sample_width = reader.getsampwidth()
        frame_bytes = int(sample_rate * frame_ms / 1000) * sample_width
        raw_frames = reader.readframes(reader.getnframes())

    voiced_chunks: list[bytes] = []
    for offset in range(0, len(raw_frames), frame_bytes):
        chunk = raw_frames[offset : offset + frame_bytes]
        if not chunk:
            continue
        rms = audioop.rms(chunk, sample_width)
        if rms >= threshold:
            voiced_chunks.append(chunk)

    target = voiced_chunks if voiced_chunks else [raw_frames]
    with wave.open(output_wav_path, "wb") as writer:
        writer.setparams(params)
        writer.writeframes(b"".join(target))
    return output_wav_path


def reduce_noise_if_enabled(input_wav_path: str, output_wav_path: str, enabled: bool) -> str:
    if not enabled:
        return input_wav_path

    try:
        import numpy as np
        import noisereduce as nr

        with wave.open(input_wav_path, "rb") as reader:
            params = reader.getparams()
            frames = reader.readframes(reader.getnframes())
            waveform = np.frombuffer(frames, dtype=np.int16)
            reduced = nr.reduce_noise(y=waveform.astype(float), sr=reader.getframerate())

        with wave.open(output_wav_path, "wb") as writer:
            writer.setparams(params)
            writer.writeframes(reduced.astype("int16").tobytes())
        return output_wav_path
    except Exception:
        return input_wav_path


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

