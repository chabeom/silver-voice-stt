# Silver Voice STT MVP

고령자 및 구음장애 사용자의 한국어 비표준 발화를 더 잘 인식하기 위한 서비스형 STT MVP입니다.  
웹 업로드/녹음, 비동기 STT 처리, 결과 수정, 관리자 분석, AI-Hub 기반 학습 파이프라인까지 한 저장소 안에 구성되어 있습니다.

## 주요 폴더

- `apps/web`: Next.js 프론트엔드
- `apps/api`: FastAPI 백엔드 API
- `services/stt_inference`: Whisper/faster-whisper 추론 로직
- `services/training_pipeline`: AI-Hub 데이터 전처리 및 fine-tuning 파이프라인
- `infrastructure`: Docker Compose, nginx 설정
- `docs`: 설계 문서, 인포그래픽, 프로젝트 요약 PDF

## 실행 전 준비

필수:
- Docker Desktop
- PowerShell 또는 CMD

프로젝트 루트:

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
```

`.env` 파일이 없으면 먼저 생성:

```powershell
Copy-Item .env.example .env
```

## 서비스 실행 명령어

### 빠른 실행: 웹 화면만 켜기

PowerShell에서 Docker Desktop을 먼저 실행한 뒤 아래 명령을 실행합니다.

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d web
```

처음 실행하거나 이미지가 오래됐으면 빌드까지 같이 실행합니다.

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml up --build -d web
```

웹 접속 주소:

```text
http://localhost:3000
```

참고: `web`만 실행해도 Docker Compose 의존성 때문에 `api`, `postgres`, `redis`, `minio`가 함께 켜질 수 있습니다.

### 1. 전체 서비스 실행

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d
```

### 2. 처음부터 다시 빌드해서 실행

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml up --build -d
```

### 3. 특정 서비스만 실행

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d web api worker
```

### 4. 서비스 중지

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml down
```

### 5. 상태 확인

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml ps
```

### 6. 로그 보기

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml logs -f
```

### 7. 웹만 다시 시작

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d --force-recreate web
```

## 접속 주소

- 웹: [http://localhost:3000](http://localhost:3000)
- API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)
- API 헬스체크: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- MinIO 콘솔: [http://localhost:9001](http://localhost:9001)

기본 관리자 계정:

- 이메일: `admin@silvervoice.example.com`
- 비밀번호: `Admin123!`

## 학습 파이프라인 실행 명령어

학습은 보통 Docker 서비스와 별도로 실행합니다.  
권장 방식은 `원본 데이터는 NAS`, `학습용 작업 폴더는 로컬 SSD`입니다.

### 1. 학습 의존성 설치

```powershell
cd "C:\Users\bumji\source\repos\sw 산학\services\training_pipeline"
py -3 -m pip install -r requirements.txt
```

### 2. `PYTHONPATH` 설정

```powershell
$env:PYTHONPATH = "C:\Users\bumji\source\repos\sw 산학\services\training_pipeline"
```

### 3. AI-Hub 데이터 전처리 / manifest 생성

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
py -3 services\training_pipeline\scripts\prepare_aihub_dataset.py `
  --dataset-root "C:\Users\bumji\source\repos\sw 산학\training data" `
  --output-dir "C:\Users\bumji\source\repos\sw 산학\training data\processed\sample_manifest"
```

### 4. Whisper fine-tuning 실행

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
$env:PYTHONPATH = "C:\Users\bumji\source\repos\sw 산학\services\training_pipeline"
py -3 services\training_pipeline\scripts\train_whisper.py `
  --model-name-or-path openai/whisper-small `
  --train-manifest "C:\Users\bumji\source\repos\sw 산학\training data\processed\sample_manifest\train.jsonl" `
  --valid-manifest "C:\Users\bumji\source\repos\sw 산학\training data\processed\sample_manifest\valid.jsonl" `
  --test-manifest "C:\Users\bumji\source\repos\sw 산학\training data\processed\sample_manifest\test.jsonl" `
  --output-dir "C:\Users\bumji\source\repos\sw 산학\models\whisper-ko-elderly-sample" `
  --train-strategy lora-encoder `
  --batch-size 2 `
  --eval-batch-size 2 `
  --epochs 3
```

### 5. 평가 스크립트 실행

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
$env:PYTHONPATH = "C:\Users\bumji\source\repos\sw 산학\services\training_pipeline"
py -3 services\training_pipeline\scripts\evaluate_model.py `
  --prediction-file "C:\Users\bumji\source\repos\sw 산학\평가결과파일경로.jsonl"
```

## 환경 변수 메모

주요 환경 변수는 `.env.example`에 정리되어 있습니다.

중요 항목:
- `NEXT_PUBLIC_API_BASE_URL`
- `DATABASE_URL`
- `REDIS_URL`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `STT_MODEL_BACKEND`
- `STT_MODEL_PATH`
- `STT_MOCK_MODE`

주의:
- `.env`는 실제 비밀값이 들어갈 수 있으므로 Git에 올리지 않습니다.
- `.env.example`만 저장소에 포함합니다.

## 개발 메모

- 현재 프론트엔드는 `apps/web`
- 현재 백엔드는 `apps/api`
- STT 추론 서비스는 `services/stt_inference`
- 학습 파이프라인은 `services/training_pipeline`

문서:
- [아키텍처](</C:/Users/bumji/source/repos/sw 산학/docs/architecture.md>)
- [폴더 구조](</C:/Users/bumji/source/repos/sw 산학/docs/folder-structure.md>)
- [DB 스키마](</C:/Users/bumji/source/repos/sw 산학/docs/db-schema.md>)
- [API 명세](</C:/Users/bumji/source/repos/sw 산학/docs/api-spec.md>)
- [프로젝트 요약 PDF](</C:/Users/bumji/source/repos/sw 산학/docs/project-status-summary.pdf>)

## 트러블슈팅

### `http://localhost:3000`이 안 뜨는 경우

먼저 Docker Desktop이 켜져 있는지 확인합니다. Docker가 꺼져 있으면 브라우저에 `ERR_CONNECTION_REFUSED`가 뜰 수 있습니다.

상태 확인:

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml ps
```

웹만 다시 실행:

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d web
```

웹 로그 확인:

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml logs -f web
```

### `.env`를 못 찾는 경우

프로젝트 루트에서 실행해야 합니다.

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
docker compose --env-file .env -f infrastructure/docker-compose.yml ps
```

### 웹 화면이 이전 캐시처럼 보이는 경우

```powershell
cd "C:\Users\bumji\source\repos\sw 산학"
if (Test-Path "apps/web/.next") { Remove-Item "apps/web/.next" -Recurse -Force }
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d --force-recreate web
```

브라우저에서는 `Ctrl + F5`로 강력 새로고침하면 됩니다.
