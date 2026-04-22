# 폴더 구조 제안

```text
/apps
  /web
  /api
/services
  /stt_inference
  /training_pipeline
/packages
  /shared-types
  /ui
/infrastructure
  docker-compose.yml
  /nginx
/docs
```

## 폴더/파일 역할

### `/apps/web`
- 사용자와 관리자 UI
- App Router 페이지, 업로드/녹음/결과/대시보드 컴포넌트 포함

### `/apps/api`
- FastAPI 애플리케이션
- 인증, 파일 업로드, 작업 제어, 결과 저장, 관리자 API 담당

### `/services/stt_inference`
- Whisper 래퍼, 오디오 전처리, 후처리, confidence 계산 로직

### `/services/training_pipeline`
- AI-Hub 원천 데이터를 학습 가능한 manifest로 바꾸는 스크립트
- train/valid/test split, 학습/평가 예시 포함

### `/packages/shared-types`
- Job, Transcript, Admin Stat 등의 공통 TS 타입

### `/packages/ui`
- 버튼, 카드, 프로그레스, 배지 등 공통 UI 컴포넌트

### `/infrastructure`
- Docker Compose, Nginx reverse proxy, 향후 배포용 운영 설정

### `/docs`
- 아키텍처, DB 스키마, REST API 명세, 시퀀스 흐름 문서

