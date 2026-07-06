# Silver Voice NAS Inference API

이 API는 NAS GPU에서 최신 LoRA STT 모델을 로딩하고, 업로드된 음성 파일을 STT 결과 JSON으로 반환한다.

## 기본 모델

```text
Base model: openai/whisper-medium
Adapter: models/whisper-medium-forced-v1-trip
```

## NAS 실행

```bash
cd ~/nas_private/nas_training_bundle
source ~/nas_private/stt-venv/bin/activate
bash scripts/run-nas-inference-api.sh
```

기본 포트는 `9001`이다.

## 확인

```bash
curl http://127.0.0.1:9001/health
curl -X POST http://127.0.0.1:9001/warmup
```

## 음성 테스트

```bash
curl -X POST http://127.0.0.1:9001/transcribe \
  -F "file=@sample.wav"
```

긴 음성은 기본적으로 30초 단위로 나누어 구간별 STT를 수행한다.

```bash
curl -X POST http://127.0.0.1:9001/transcribe \
  -F "file=@sample.wav" \
  -F "chunk_seconds=30" \
  -F "chunk_overlap_seconds=0"
```

응답은 백엔드가 DB에 저장하기 쉬운 `full_text`, `segments`, `confidence`, `duration` 형태로 반환된다.
