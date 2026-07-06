# NAS 내부 프론트엔드 STT 테스트 절차

이 문서는 로컬 노트북에서 NAS의 `9001` 포트에 직접 접근하기 어려운 상황을 기준으로 정리한 실행 절차입니다. 프론트엔드, 백엔드, STT 추론 API를 모두 NAS/JupyterLab 내부에서 실행하고, 사용자는 Jupyter proxy 주소로 프론트엔드에 접속합니다.

## 실행 구조

```text
사용자 브라우저
-> Jupyter proxy 프론트엔드 3000 포트
-> NAS 내부 백엔드 8000 포트
-> NAS 내부 STT 추론 API 9001 포트
-> whisper-medium-forced-v1-trip 모델
```

## 1. STT 추론 API 실행

NAS JupyterLab 터미널 1에서 실행합니다.

```bash
cd ~/nas_private/nas_training_bundle
source ~/nas_private/stt-venv/bin/activate
bash scripts/run-nas-inference-api.sh
```

다른 NAS 터미널에서 상태를 확인합니다.

```bash
curl http://127.0.0.1:9001/health
```

`status: ok`, `adapter_exists: true`, `device: cuda`가 보이면 정상입니다.

## 2. 프로젝트 clone 또는 최신화

NAS JupyterLab 터미널 2에서 실행합니다.

```bash
cd ~/nas_private
git clone <GITHUB_REPOSITORY_URL> silver-voice-stt
cd silver-voice-stt
```

이미 clone되어 있으면 다음처럼 최신화합니다.

```bash
cd ~/nas_private/silver-voice-stt
git pull
```

## 3. NAS 웹/API 의존성 설치

```bash
cd ~/nas_private/silver-voice-stt
bash scripts/setup-nas-internal-web.sh
```

기본적으로 기존 `~/nas_private/stt-venv`를 재사용합니다. 별도 가상환경을 만들고 싶으면 다음처럼 실행합니다.

```bash
WEB_VENV_DIR=~/nas_private/silver-voice-web-venv bash scripts/setup-nas-internal-web.sh
```

## 4. 백엔드와 프론트엔드 실행

```bash
cd ~/nas_private/silver-voice-stt
bash scripts/run-nas-internal-web.sh
```

이 스크립트는 다음 설정을 자동으로 적용합니다.

```text
DATABASE_URL=sqlite:///.../silver_voice_nas.db
STORAGE_BACKEND=local
CELERY_TASK_ALWAYS_EAGER=true
STT_MODEL_BACKEND=nas-api
STT_REMOTE_API_URL=http://127.0.0.1:9001/transcribe
NEXT_PUBLIC_API_BASE_URL=/user/<JUPYTER_USER>/proxy/8000/api/v1
```

`CELERY_TASK_ALWAYS_EAGER=true`이므로 Redis와 별도 Worker 없이 백엔드 요청 안에서 STT 작업이 바로 실행됩니다. 운영 환경에서는 Redis/Worker를 분리하는 것이 좋지만, NAS 내부 테스트에는 이 방식이 가장 단순합니다.

## 5. 브라우저 접속

Jupyter proxy 주소로 프론트엔드에 접속합니다.

```text
http://61.81.98.88:8000/user/s202110742/proxy/3000/
```

사용자명이 다르면 `s202110742` 부분을 본인 Jupyter 사용자명으로 바꿉니다.

## 6. 문제 확인 명령어

API 로그 확인:

```bash
tail -f ~/nas_private/silver-voice-stt/logs/nas-internal-api.log
```

STT API 상태 확인:

```bash
curl http://127.0.0.1:9001/health
```

백엔드 상태 확인:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

프론트엔드 API 주소 확인:

```bash
echo "$NEXT_PUBLIC_API_BASE_URL"
```

## 참고

- NAS 추론 API는 `whisper-medium-forced-v1-trip` 어댑터를 사용합니다.
- 백엔드는 로컬 파일 저장소와 SQLite를 사용하므로 PostgreSQL, Redis, MinIO 없이도 업로드 및 STT 테스트가 가능합니다.
- 로컬 노트북에서 NAS `9001` 포트 접근이 막히는 경우가 있어, 프론트엔드와 백엔드를 NAS 내부에서 같이 실행하는 방식을 사용합니다.
