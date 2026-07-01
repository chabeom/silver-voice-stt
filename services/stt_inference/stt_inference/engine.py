from __future__ import annotations

from pathlib import Path

from stt_inference.confidence import logprob_to_confidence


class WhisperEngine:
    def __init__(
        self,
        *,
        model_path: str,
        download_root: str,
        device: str,
        compute_type: str,
        beam_size: int,
        best_of: int,
        mock_mode: bool,
    ) -> None:
        self.mock_mode = mock_mode
        self.model_path = model_path
        self.download_root = download_root
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.best_of = best_of
        self._model = None

        if not self.mock_mode:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                model_path,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
            )

    def transcribe(self, input_path: str, display_name: str | None = None) -> dict:
        if self.mock_mode:
            base_name = Path(display_name or input_path).stem.replace("_", " ").strip()
            if not base_name:
                base_name = "\uC5C5\uB85C\uB4DC\uD55C \uC74C\uC131"

            text = (
                f"{base_name}\uC5D0 \uB300\uD55C \uB370\uBAA8 \uACB0\uACFC\uC785\uB2C8\uB2E4. "
                "\uC2E4\uC81C Whisper \uBAA8\uB378\uC744 \uC5F0\uACB0\uD558\uBA74 "
                "\uC774 \uC601\uC5ED\uC5D0 \uC74C\uC131 \uC778\uC2DD \uACB0\uACFC\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4."
            )
            return {
                "language": "ko",
                "segments": [
                    {
                        "segment_index": 0,
                        "start_sec": 0.0,
                        "end_sec": 2.4,
                        "text": text,
                        "confidence": 0.78,
                        "raw_confidence": 0.78,
                        "avg_logprob": -0.24,
                        "no_speech_prob": 0.03,
                        "tokens_json": [
                            {
                                "word": "\uB370\uBAA8",
                                "start": 0.0,
                                "end": 0.4,
                                "probability": 0.84,
                            }
                        ],
                    }
                ],
            }

        segments, info = self._model.transcribe(
            input_path,
            language="ko",
            vad_filter=False,
            beam_size=self.beam_size,
            best_of=self.best_of,
            word_timestamps=True,
        )

        serialized_segments = []
        for index, segment in enumerate(segments):
            words = [
                {
                    "word": word.word,
                    "start": float(word.start or 0.0),
                    "end": float(word.end or 0.0),
                    "probability": float(word.probability or 0.0),
                }
                for word in (segment.words or [])
            ]
            avg_logprob = float(getattr(segment, "avg_logprob", 0.0))
            raw_confidence = logprob_to_confidence(avg_logprob)
            serialized_segments.append(
                {
                    "segment_index": index,
                    "start_sec": float(segment.start),
                    "end_sec": float(segment.end),
                    "text": segment.text.strip(),
                    "confidence": raw_confidence,
                    "raw_confidence": raw_confidence,
                    "avg_logprob": avg_logprob,
                    "no_speech_prob": float(getattr(segment, "no_speech_prob", 0.0)),
                    "tokens_json": words,
                }
            )

        return {"language": info.language or "ko", "segments": serialized_segments}
