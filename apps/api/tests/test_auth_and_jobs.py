def register_and_login(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "full_name": "홍길동", "password": "StrongPass123!"},
    )
    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "StrongPass123!"})
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me(client):
    token = register_and_login(client)
    response = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_upload_and_create_job(client):
    token = register_and_login(client)
    upload_response = client.post(
        "/api/v1/uploads/audio",
        headers=auth_headers(token),
        data={"upload_source": "file", "metadata_json": '{"browser":"pytest"}'},
        files={"file": ("sample.wav", b"RIFF....WAVEfmt ", "audio/wav")},
    )
    assert upload_response.status_code == 201
    job_id = upload_response.json()["id"]

    create_response = client.post(
        "/api/v1/jobs",
        headers=auth_headers(token),
        json={
            "audio_job_id": job_id,
            "enable_noise_reduction": False,
            "enable_speaker_diarization": True,
            "expected_speakers": 2,
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["status"] == "queued"

    delete_response = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers(token))
    assert delete_response.status_code == 409


def test_delete_uploaded_job(client):
    token = register_and_login(client)
    upload_response = client.post(
        "/api/v1/uploads/audio",
        headers=auth_headers(token),
        data={"upload_source": "file", "metadata_json": '{"browser":"pytest"}'},
        files={"file": ("delete-me.wav", b"RIFF....WAVEfmt ", "audio/wav")},
    )
    assert upload_response.status_code == 201
    job_id = upload_response.json()["id"]

    delete_response = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers(token))
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers(token))
    assert get_response.status_code == 404


def test_delete_completed_job_removes_transcript_and_corrections(client):
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import AudioJob, Correction, Transcript, TranscriptSegment
    from app.services.job_service import save_transcription_result

    token = register_and_login(client)
    upload_response = client.post(
        "/api/v1/uploads/audio",
        headers=auth_headers(token),
        data={"upload_source": "file", "metadata_json": '{"browser":"pytest"}'},
        files={"file": ("completed.wav", b"RIFF....WAVEfmt ", "audio/wav")},
    )
    assert upload_response.status_code == 201
    job_id = upload_response.json()["id"]

    with SessionLocal() as db:
        job = db.get(AudioJob, job_id)
        transcript = save_transcription_result(
            db,
            job=job,
            result={
                "language": "ko",
                "full_text": "원문",
                "normalized_text": "원문",
                "average_confidence": 0.9,
                "low_confidence_ratio": 0.0,
                "duration": 1.5,
                "segments": [
                    {
                        "segment_index": 0,
                        "start_sec": 0.0,
                        "end_sec": 1.5,
                        "text": "원문",
                        "normalized_text": "원문",
                        "confidence": 0.9,
                        "is_low_confidence": False,
                    }
                ],
            },
            processing_ms=100,
        )
        db.add(
            Correction(
                job_id=job_id,
                transcript_id=transcript.id,
                user_id=job.user_id,
                original_text="원문",
                corrected_text="수정문",
                average_confidence=0.9,
                diff_json={},
                environment_metadata_json={},
            )
        )
        db.commit()

    delete_response = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers(token))
    assert delete_response.status_code == 204

    with SessionLocal() as db:
        assert db.get(AudioJob, job_id) is None
        assert db.scalar(select(Transcript).where(Transcript.job_id == job_id)) is None
        assert db.scalar(select(TranscriptSegment).join(Transcript).where(Transcript.job_id == job_id)) is None
        assert db.scalar(select(Correction).where(Correction.job_id == job_id)) is None
