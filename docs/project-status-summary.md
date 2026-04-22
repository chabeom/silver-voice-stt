# Silver Voice STT 프로젝트 현황 정리

## 1. 프로젝트 개요

Silver Voice STT는 고령자와 구음장애 사용자의 비표준 한국어 발화를 더 잘 인식하기 위한 서비스형 STT MVP다.  
현재 구조는 `웹 업로드/녹음 -> FastAPI API -> MinIO 저장 -> Celery Worker -> Whisper 계열 추론 -> PostgreSQL 저장 -> SSE 상태 반영 -> 결과 수정/관리자 분석` 흐름으로 동작한다.

## 2. 현재 구현된 기능

### 사용자 웹
- 홈 화면, 로그인, 회원가입, 음성 업로드, 작업 조회, 결과 상세 페이지 구현
- 파일 업로드와 브라우저 마이크 녹음 지원
- 업로드 진행률 표시
- SSE 기반 작업 상태 표시
- STT 결과 텍스트, 문장별 timestamp, confidence 표시
- 낮은 confidence 구간 강조 표시
- 사용자가 결과 텍스트를 직접 수정하고 저장 가능

### 관리자 웹
- 전체 업로드/처리 이력 조회
- 원본 음성 재생
- 예측문과 수정문 비교
- confidence 평균, 처리 시간, 오류율 통계 표시
- 모델 버전별 비교 화면
- correction 데이터 export

### 백엔드/API
- JWT 기반 회원가입, 로그인, 토큰 재발급, 내 정보 조회
- 음성 업로드 API
- STT 작업 생성, 상태 조회, 결과 조회 API
- 결과 수정 저장 API
- 관리자 통계, 상세 분석, correction export API
- PostgreSQL, Redis, MinIO, Celery 연동

### STT 추론
- 16kHz mono 변환
- VAD 및 기본 전처리 파이프라인
- Whisper 계열 추론 래퍼
- segment 단위 timestamp 및 confidence 계산
- 띄어쓰기/숫자/날짜/전화번호/군더더기 발화 정리용 후처리 구조
- `STT_MOCK_MODE`와 실제 로컬 모델 추론 모드 분리

### 학습 파이프라인
- AI-Hub 샘플 데이터 파서 리팩토링 완료
- `01.원천데이터`, `02.라벨링데이터` 구조 자동 인식
- 긴 자유대화 wav를 학습용 짧은 segment로 분할
- train/valid/test manifest 생성
- CSV correction export도 재학습 입력으로 로드 가능하게 확장
- Whisper fine-tuning용 실제 Trainer 골격 구현
- `full`, `encoder-only`, `lora`, `lora-encoder` 전략 지원
- 샘플 데이터 기준 `96`개 학습용 세그먼트 생성 검증 완료

## 3. 이번 리팩토링 요약

### 정리한 영역
- `dataset.py`: AI-Hub 라벨 파싱, 인코딩 fallback, transcript 정규화, segment 분할 로직 추가
- `manifest.py`: JSONL 로드, split 안정화, 요약 통계 함수 추가
- `trainer.py`: no-op stub 제거, 실제 Whisper 학습 루프 구조로 교체
- `prepare_aihub_dataset.py`: 샘플 데이터 자동 탐색 및 세그먼트 manifest 생성 개선
- `train_whisper.py`: 실제 학습 옵션 CLI 인자 확장
- 테스트 추가: transcript 추출, split, CSV correction 로드, turn segmentation 검증

### 리팩토링 결과
- 샘플 데이터 구조가 달라도 처리 경로를 한 군데에서 관리 가능
- 긴 대화 음성을 학습 가능한 짧은 단위로 자동 분할 가능
- correction CSV와 AI-Hub 샘플 데이터를 동일 파이프라인으로 합칠 기반 마련
- 실제 학습 코드가 들어갈 자리를 넘어서, HF Trainer/PEFT 구조로 바로 실행 가능한 수준까지 골격 확보

## 4. 샘플 데이터 검증 결과

- 데이터 위치: `C:\Users\bumji\source\repos\sw 산학\training data`
- 전처리 결과 폴더: `C:\Users\bumji\source\repos\sw 산학\training data\processed\sample_manifest`
- 생성된 학습 세그먼트 수: `96`
- split 결과:
  - train: `76`
  - valid: `10`
  - test: `10`
- 최대 세그먼트 길이: `27.997초`
- 평균 세그먼트 길이: `21.065초`

## 5. 아직 구현이 덜 된 기능

### 실제 학습 실행
- 현재 PC에는 `torch`, `transformers`, `datasets`, `peft`, `soundfile`, `pytest`가 아직 설치되지 않음
- 따라서 학습 코드는 준비됐지만 실제 fine-tuning은 아직 실행하지 않음
- 현재 GPU는 AMD 계열이라 일반적인 CUDA 기반 Whisper 학습 환경과는 다름

### 데이터 품질 고도화
- 현재 자유대화 샘플은 질문/답변 단위 기반의 근사 segmentation 사용
- 향후 forced alignment 또는 WhisperX/VAD 기반 정렬이 필요
- AI-Hub 전체 본데이터 스키마 차이에 대한 추가 케이스 보강 필요

### 운영 배포
- 학습 완료 모델을 CTranslate2/faster-whisper 추론용으로 자동 변환하는 단계 미구현
- `model_versions` 자동 등록과 운영 모델 승격 배치 미구현
- correction export의 운영 배치 자동화 미구현

### 서비스 완성도
- 관리자 분석 지표 세분화 필요
- 테스트 커버리지 확대 필요
- CI/CD, 백업, 모니터링, 알림 체계 필요
- 보안 고도화와 역할 기반 권한 분리 강화 필요

## 6. 앞으로 구현해야 할 우선순위

### 1단계
- 학습 환경 설치
- 샘플 데이터로 1차 Whisper fine-tuning 실행
- WER/CER 측정

### 2단계
- AI-Hub 전체 데이터셋 정식 전처리
- forced alignment 기반 세그먼트 정교화
- correction 데이터와 AI-Hub 데이터를 합친 재학습셋 구성

### 3단계
- 학습 결과를 CTranslate2로 변환
- 운영 추론 서비스에 새 모델 버전 연결
- 관리자 화면에서 모델별 성능 비교 자동화

### 4단계
- 운영 로그/모니터링/배포 자동화
- 역할 기반 권한 강화
- 공공/돌봄 환경용 장기 운영 시나리오 대응

## 7. 결론

현재 프로젝트는 단순 데모 단계를 넘어, 실제 서비스형 MVP의 전체 구조와 학습 파이프라인 골격까지 갖춘 상태다.  
다만 AI-Hub 기반 fine-tuning은 아직 "실행 가능한 코드와 데이터 준비 완료" 단계이며, 실제 학습 실행과 운영 배포 자동화는 다음 단계에서 이어서 구현해야 한다.
