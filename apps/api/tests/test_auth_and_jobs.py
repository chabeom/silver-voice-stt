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
        json={"audio_job_id": job_id, "enable_noise_reduction": False},
    )
    assert create_response.status_code == 201
    assert create_response.json()["status"] == "queued"

