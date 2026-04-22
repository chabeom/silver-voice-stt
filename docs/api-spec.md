# REST API 명세

## 설계 이유

- 사용자 흐름과 관리자 흐름을 URL 네임스페이스로 분리해 권한 검증을 단순하게 유지한다.
- 업로드와 STT 실행을 분리해 향후 배치 등록, 모델 선택 실행, 재처리 기능을 붙이기 쉽다.
- 결과 수정 저장 API는 correction 데이터셋 적재와 운영 감사 로그를 한 번에 처리한다.

## 인증

### `POST /api/v1/auth/register`
- 설명: 사용자 회원가입
- 요청:
```json
{
  "email": "user@example.com",
  "full_name": "홍길동",
  "password": "StrongPass123!"
}
```
- 응답: `201 Created`

### `POST /api/v1/auth/login`
- 설명: 액세스/리프레시 토큰 발급
- 요청:
```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

### `POST /api/v1/auth/refresh`
- 설명: 리프레시 토큰으로 액세스 토큰 재발급

### `GET /api/v1/auth/me`
- 설명: 현재 사용자 프로필

## 사용자 API

### `POST /api/v1/uploads/audio`
- 설명: 음성 파일 업로드
- 형식: `multipart/form-data`
- 필드:
  - `file`
  - `upload_source`: `file | microphone`
  - `metadata_json`: JSON 문자열
- 응답:
```json
{
  "id": "job-id",
  "status": "uploaded",
  "original_filename": "sample.wav"
}
```

### `POST /api/v1/jobs`
- 설명: STT 작업 생성 및 queue 등록
- 요청:
```json
{
  "audio_job_id": "job-id",
  "model_version_id": "optional-model-id",
  "enable_noise_reduction": false
}
```

### `GET /api/v1/jobs`
- 설명: 내 작업 목록 조회
- 쿼리: `status`, `page`, `page_size`

### `GET /api/v1/jobs/{job_id}`
- 설명: 작업 상태 조회

### `GET /api/v1/jobs/{job_id}/events`
- 설명: SSE 기반 진행률 스트림

### `GET /api/v1/jobs/{job_id}/result`
- 설명: STT 결과 상세 조회
- 응답 필드:
  - 전체 텍스트
  - segment 목록
  - timestamp
  - confidence
  - low-confidence 플래그
  - 모델 버전

### `PUT /api/v1/jobs/{job_id}/result`
- 설명: 사용자가 정정한 결과 저장
- 요청:
```json
{
  "corrected_text": "정정된 최종 문장",
  "environment_metadata": {
    "browser": "Chrome",
    "device": "tablet"
  }
}
```

### `GET /api/v1/models`
- 설명: 사용 가능한 모델 버전 조회

## 관리자 API

### `GET /api/v1/admin/jobs`
- 설명: 전체 업로드/처리 이력 조회
- 필터:
  - `status`
  - `model_version_id`
  - `min_confidence`
  - `has_correction`
  - `failed_only`

### `GET /api/v1/admin/jobs/{job_id}`
- 설명: 원본 음성, 예측문, 수정문, segment, 로그 포함 상세 조회

### `GET /api/v1/admin/stats/overview`
- 설명: 평균 confidence, 처리시간, 실패율, correction rate 반환

### `GET /api/v1/admin/stats/model-comparison`
- 설명: 모델 버전별 처리량, 평균 confidence, correction rate 비교

### `GET /api/v1/admin/export/corrections`
- 설명: 재학습용 correction 데이터 CSV export

## 공통 응답 규칙

- 인증 실패: `401`
- 권한 부족: `403`
- 리소스 없음: `404`
- 파일 형식/크기 오류: `422`
- 작업 중복 실행: `409`
- 내부 실패: `500`

