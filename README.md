# Silver Voice STT MVP

고령자와 구음장애 사용자의 비표준 한국어 발화에 특화된 Whisper 기반 STT 서비스형 MVP다.  
상용 API 없이 오픈소스 스택만으로 업로드, 비동기 추론, 결과 정정, 관리자 분석, 재학습 피드백 루프까지 한 번에 연결되도록 설계했다.

## 구성 요약

- `apps/web`: Next.js 14, TypeScript, Tailwind, Recharts 기반 사용자/관리자 웹
- `apps/api`: FastAPI, SQLAlchemy, JWT, Celery, Redis, MinIO 연동 API
- `services/stt_inference`: 오디오 전처리, Whisper 추론, confidence, 후처리
- `services/training_pipeline`: AI-Hub 데이터 전처리, split, 학습/평가 스크립트
- `infrastructure/docker-compose.yml`: 로컬 MVP 실행 인프라

## 문서 순서

1. [아키텍처 설명](C:\Users\bumji\source\repos\sw 산학\docs\architecture.md)
2. [폴더 구조](C:\Users\bumji\source\repos\sw 산학\docs\folder-structure.md)
3. [DB 스키마](C:\Users\bumji\source\repos\sw 산학\docs\db-schema.md)
4. [REST API 명세](C:\Users\bumji\source\repos\sw 산학\docs\api-spec.md)

## 빠른 실행

```bash
cp .env.example .env
docker compose -f infrastructure/docker-compose.yml up --build
```

- Web: [http://localhost:3000](http://localhost:3000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- MinIO console: [http://localhost:9001](http://localhost:9001)
- 기본 관리자 계정: `admin@silvervoice.example.com / Admin123!`

## 개발 포인트

- 기본값은 `STT_MOCK_MODE=true`라서 GPU 없이도 전체 플로우를 검증할 수 있다.
- 실제 모델을 쓰려면 `STT_MODEL_PATH`, `STT_DEVICE`, `STT_COMPUTE_TYPE`를 조정하면 된다.
- correction export 결과는 `services/training_pipeline` 입력 manifest로 바로 연결할 수 있다.

## 포함된 기능

- 사용자 웹
  - 음성 파일 업로드
  - 브라우저 마이크 녹음
  - 업로드 진행률 표시
  - SSE 기반 작업 상태 표시
  - 문장별 timestamp / confidence / low-confidence 강조
  - 결과 수정 및 저장
- 관리자 웹
  - 업로드 이력 조회
  - 예측문 / 수정문 비교
  - 모델별 신뢰도/처리시간 통계
  - correction export
- 백엔드
  - JWT 인증
  - FastAPI + Celery + Redis + PostgreSQL + MinIO
  - Whisper 추론 모듈 연동
  - correction feedback loop 저장

## 추후 학습 파이프라인 연결

1. AI-Hub 원천 데이터 다운로드
2. `services/training_pipeline/scripts/prepare_aihub_dataset.py` 실행
3. `train_whisper.py`로 fine-tuning
4. `evaluate_model.py`로 WER/CER 측정
5. 새 모델 아티팩트를 `model_versions`에 등록 후 활성화
