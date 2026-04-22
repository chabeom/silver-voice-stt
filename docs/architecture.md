# Silver Voice STT 아키텍처

## 1. 아키텍처 설명

이 MVP는 `업로드/녹음 UI -> FastAPI API -> MinIO 저장 -> Celery Worker -> Whisper 추론 -> PostgreSQL 저장 -> SSE 상태 스트리밍 -> 사용자/관리자 화면` 흐름으로 동작한다.

이렇게 분리한 이유는 다음과 같다.

- 웹과 API를 분리해 고령층 친화 UI 개선과 AI 파이프라인 변경을 서로 독립적으로 배포할 수 있다.
- 업로드와 추론을 분리해 긴 STT 작업이 HTTP 요청 시간을 점유하지 않도록 한다.
- MinIO를 통해 원본 음성과 전처리 음성을 안전하게 보관하고, 재학습 데이터셋으로 재사용할 수 있다.
- PostgreSQL은 정정 이력, 모델 버전, 감사 로그까지 일관되게 남길 수 있어 운영성과 추적성이 높다.
- Redis/Celery는 추론 재시도, 백그라운드 처리, 향후 배치 재학습 적재에 유리하다.

## 2. 서비스 경계

### `apps/web`
- Next.js 14 App Router 기반 사용자/관리자 UI
- 업로드 진행률, SSE 상태 수신, 정정 편집, 관리자 통계 시각화 담당

### `apps/api`
- 인증, 업로드, 작업 관리, 결과 조회/수정, 관리자 통계 API 제공
- PostgreSQL, Redis, MinIO, Celery와 연결되는 핵심 오케스트레이션 레이어

### `services/stt_inference`
- 오디오 전처리, VAD, 노이즈 감소, Whisper 추론, confidence 계산, 후처리 로직 담당
- 실시간 API 서버와 분리된 독립 모듈로 유지해 모델 교체/최적화가 쉽다

### `services/training_pipeline`
- AI-Hub 고령자/구음장애 데이터를 재학습용 manifest로 가공
- split, train, evaluate, export workflow 제공

### `packages/shared-types`
- 프론트/백엔드 계약을 TS 타입으로 고정

### `packages/ui`
- 고령층 친화 공통 UI 컴포넌트

## 3. 핵심 런타임 흐름

1. 사용자가 업로드 또는 녹음 파일 전송
2. API가 파일 형식/용량 검증 후 MinIO 저장
3. API가 `audio_jobs` 레코드 생성
4. API가 STT 작업 생성 시 Celery task enqueue
5. Worker가 오디오를 16kHz mono WAV로 변환
6. Worker가 VAD와 선택적 노이즈 감소 적용
7. Whisper 계열 모델로 segment 단위 추론
8. confidence/low-confidence 구간 계산
9. 후처리(띄어쓰기/숫자/날짜/전화번호/군더더기 보정)
10. `transcripts`, `transcript_segments` 저장
11. 웹은 SSE로 진행률을 받고 결과를 렌더링
12. 사용자가 정정하면 `corrections`와 `audit_logs`에 누적

## 4. 시퀀스 다이어그램 설명

### 업로드 -> job 생성 -> worker 처리 -> 추론 -> 저장 -> 결과 조회

1. 사용자가 웹의 업로드/녹음 페이지에서 음성 파일을 전송한다.
2. 프론트는 업로드 진행률을 표시하며 `/uploads/audio`에 multipart 요청을 보낸다.
3. FastAPI는 JWT 인증 후 파일 형식과 최대 용량을 검사하고 MinIO에 파일을 저장한다.
4. API는 `audio_jobs`에 `uploaded` 상태 레코드를 만든다.
5. 사용자가 STT 실행을 요청하거나 기본 자동 실행 옵션이 켜져 있으면 `/jobs`가 호출된다.
6. API는 `audio_jobs.status=queued`로 변경하고 Celery task ID를 저장한다.
7. Worker는 MinIO에서 원본 파일을 내려받고 전처리를 수행한다.
8. Worker는 현재 활성 모델 버전 또는 요청 모델 버전으로 추론한다.
9. 결과 segment와 평균 confidence, 처리시간을 계산해 DB에 저장한다.
10. 작업 상태는 `completed` 또는 `failed`로 갱신된다.
11. 웹의 SSE 구독이 상태 변경을 받아 사용자에게 진행률과 결과를 즉시 보여준다.
12. 사용자는 `/jobs/{id}/result`로 상세 결과를 조회한다.

### 결과 수정 -> correction 저장 -> 재학습 데이터 적재

1. 사용자가 결과 상세 페이지에서 텍스트를 수정한다.
2. 프론트는 원문과 수정문을 함께 `/jobs/{id}/result`에 저장 요청한다.
3. API는 `corrections` 테이블에 원본 예측문, 수정문, 모델 버전, confidence, 업로드 환경 메타데이터를 함께 저장한다.
4. 같은 시점에 `audit_logs`에 수정 이벤트를 남긴다.
5. 관리자 또는 배치 작업은 `corrections` 데이터를 CSV/JSONL manifest로 export 한다.
6. `services/training_pipeline`이 export 산출물을 재학습용 데이터셋에 합쳐 다음 버전 학습에 사용한다.

## 5. 운영 설계 포인트

- 모델 버전은 `model_versions`로 분리해 A/B 비교와 롤백을 쉽게 한다.
- 업로드 파일은 MIME 타입, 확장자, 용량, 사용자 권한을 모두 검증한다.
- Worker는 실패 시 재시도하고, `retry_count`와 에러 메시지를 남긴다.
- 로그는 JSON 구조화 형식으로 남겨 관리자/관제 시스템 연동을 쉽게 한다.
- `STT_MOCK_MODE`를 두어 GPU가 없는 개발 환경에서도 흐름을 검증할 수 있게 한다.

