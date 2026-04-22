# DB 스키마 설계

## 설계 이유

- `audio_jobs`를 중심 엔티티로 두어 업로드와 STT 처리 상태를 하나의 라이프사이클로 관리한다.
- `transcripts`와 `transcript_segments`를 분리해 문장 단위 confidence 및 timestamp를 정교하게 다룬다.
- `corrections`는 학습 피드백 루프의 핵심이므로 원문, 수정문, 모델 버전, 메타데이터를 함께 저장한다.
- `audit_logs`는 운영 추적성과 공공/돌봄 도메인 감사 요구에 대비한다.

## 테이블

### `users`
| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | UUID 문자열 | PK |
| email | varchar(320) | 로그인 ID, unique |
| full_name | varchar(120) | 사용자 이름 |
| password_hash | varchar(255) | bcrypt/argon2 해시 |
| role | varchar(20) | `user`, `admin` |
| is_active | boolean | 계정 활성 여부 |
| created_at | timestamptz | 생성시각 |
| last_login_at | timestamptz nullable | 최근 로그인 |

### `model_versions`
| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | UUID 문자열 | PK |
| version_name | varchar(100) | 예: `whisper-ko-elderly-v0` |
| model_family | varchar(50) | `faster-whisper`, `transformers-whisper` |
| locale | varchar(20) | `ko-KR` |
| source_path | varchar(255) | 모델 디렉터리 또는 registry path |
| description | text | 운영 설명 |
| metrics_json | json | WER/CER 등 평가값 |
| is_active | boolean | 기본 모델 여부 |
| created_at | timestamptz | 등록 시각 |

### `audio_jobs`
| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | UUID 문자열 | PK |
| user_id | UUID 문자열 | FK -> users |
| model_version_id | UUID 문자열 nullable | FK -> model_versions |
| original_filename | varchar(255) | 원본 파일명 |
| mime_type | varchar(100) | MIME |
| file_size_bytes | bigint | 파일 크기 |
| duration_seconds | float nullable | 원본 길이 |
| sample_rate | integer nullable | 원본 샘플레이트 |
| channel_count | integer nullable | 원본 채널 수 |
| upload_source | varchar(20) | `file`, `microphone` |
| storage_bucket | varchar(120) | MinIO bucket |
| storage_object_key | varchar(255) | 원본 object key |
| processed_object_key | varchar(255) nullable | 전처리된 wav |
| upload_metadata_json | json | 브라우저, device, noise_level 등 |
| status | varchar(30) | `uploaded`, `queued`, `preprocessing`, `running`, `postprocessing`, `completed`, `failed` |
| progress | float | 0.0~1.0 |
| average_confidence | float nullable | 평균 confidence |
| processing_started_at | timestamptz nullable | 처리 시작 |
| completed_at | timestamptz nullable | 완료 시각 |
| error_message | text nullable | 실패 원인 |
| task_id | varchar(100) nullable | Celery task ID |
| retry_count | integer | 재시도 횟수 |
| created_at | timestamptz | 생성 |
| updated_at | timestamptz | 수정 |

### `transcripts`
| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | UUID 문자열 | PK |
| job_id | UUID 문자열 | FK -> audio_jobs, unique |
| language | varchar(20) | `ko` |
| full_text | text | 원본 예측문 |
| normalized_text | text | 후처리 반영 최종문 |
| average_confidence | float | 평균 confidence |
| low_confidence_ratio | float | 임계치 이하 segment 비율 |
| total_duration | float | 전체 길이 |
| processing_ms | integer | 처리 시간 |
| raw_result_json | json | 원시 추론 payload |
| created_at | timestamptz | 생성 |
| updated_at | timestamptz | 수정 |

### `transcript_segments`
| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | UUID 문자열 | PK |
| transcript_id | UUID 문자열 | FK -> transcripts |
| segment_index | integer | 순서 |
| start_sec | float | 시작 timestamp |
| end_sec | float | 종료 timestamp |
| text | text | 원문 segment |
| normalized_text | text | 후처리 segment |
| confidence | float | segment confidence |
| avg_logprob | float nullable | 모델 평균 로그확률 |
| no_speech_prob | float nullable | 무음 확률 |
| tokens_json | json | token 또는 word-level 정보 |
| is_low_confidence | boolean | 임계치 이하 여부 |
| created_at | timestamptz | 생성 |

### `corrections`
| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | UUID 문자열 | PK |
| job_id | UUID 문자열 | FK -> audio_jobs |
| transcript_id | UUID 문자열 | FK -> transcripts |
| user_id | UUID 문자열 | FK -> users |
| model_version_id | UUID 문자열 nullable | FK -> model_versions |
| original_text | text | 수정 전 텍스트 |
| corrected_text | text | 수정 후 텍스트 |
| average_confidence | float nullable | 수정 당시 confidence |
| diff_json | json | 단어/문장 diff |
| environment_metadata_json | json | 기기, 브라우저, 업로드 소스 등 |
| created_at | timestamptz | 생성 |

### `audit_logs`
| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | UUID 문자열 | PK |
| actor_user_id | UUID 문자열 nullable | 실행 사용자 |
| target_type | varchar(50) | `audio_job`, `transcript`, `correction`, `auth` |
| target_id | UUID 문자열 nullable | 대상 레코드 ID |
| action | varchar(50) | `upload`, `job_started`, `job_completed`, `correction_saved` 등 |
| metadata_json | json | 상세 값 |
| created_at | timestamptz | 생성 |

