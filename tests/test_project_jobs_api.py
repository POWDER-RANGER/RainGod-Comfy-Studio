"""Tests for project-backed job records, approval, and provenance."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.test_jobs_api import PROMPT_ID, _completed_history


def _use_test_store(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RAINGOD_DB_PATH", str(tmp_path / "projects.sqlite3"))


def test_create_and_read_project_persists_across_requests(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    _use_test_store(monkeypatch, tmp_path)

    created = client.post(
        "/projects", json={"name": "Sad Boy cover art", "description": "Album one"}
    )
    assert created.status_code == 201

    fetched = client.get(f"/projects/{created.json()['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Sad Boy cover art"
    assert fetched.json()["jobs"] == []


def test_project_generation_requires_explicit_approval(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    _use_test_store(monkeypatch, tmp_path)
    project = client.post("/projects", json={"name": "Cover"}).json()

    response = client.post("/generate", json={"prompt": "rainy city", "project_id": project["id"]})

    assert response.status_code == 400
    assert "approved=true" in response.json()["detail"]


def test_project_generation_records_job_approval_and_provenance(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    _use_test_store(monkeypatch, tmp_path)
    project = client.post("/projects", json={"name": "Cover"}).json()
    fake = MagicMock()
    fake.queue_prompt.return_value = "provider-prompt-123"
    monkeypatch.setattr("backend.rain_backend.client", fake)

    response = client.post(
        "/generate",
        json={
            "prompt": "rainy city",
            "seed": 8675309,
            "project_id": project["id"],
            "approved": True,
        },
    )

    assert response.status_code == 202
    result = response.json()
    saved = client.get(f"/projects/{project['id']}").json()["jobs"]
    assert len(saved) == 1
    job = saved[0]
    assert job["id"] == result["job_id"]
    assert job["provider_job_id"] == "provider-prompt-123"
    assert job["status"] == "queued"
    assert job["request"]["prompt"] == "rainy city"
    assert job["approval"]["decision"] == "approved"
    assert job["provenance"]["seed"] == 8675309
    assert job["provenance"]["workflow"] == "txt2img"


def test_project_generation_failure_is_retained_as_failed_record(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    _use_test_store(monkeypatch, tmp_path)
    project = client.post("/projects", json={"name": "Cover"}).json()
    fake = MagicMock()
    fake.queue_prompt.side_effect = RuntimeError("ComfyUI refused workflow")
    monkeypatch.setattr("backend.rain_backend.client", fake)

    response = client.post(
        "/generate",
        json={"prompt": "rainy city", "project_id": project["id"], "approved": True},
    )

    assert response.status_code == 503
    jobs = client.get(f"/projects/{project['id']}").json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["status"] == "failed"
    assert jobs[0]["error"] == "ComfyUI refused workflow"


def test_comfyui_status_refresh_updates_studio_project_job(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    _use_test_store(monkeypatch, tmp_path)
    project = client.post("/projects", json={"name": "Cover"}).json()
    fake = MagicMock()
    fake.queue_prompt.return_value = PROMPT_ID
    monkeypatch.setattr("backend.rain_backend.client", fake)
    generated = client.post(
        "/generate",
        json={"prompt": "rainy city", "project_id": project["id"], "approved": True},
    )
    assert generated.status_code == 202

    fake.get_history.return_value = _completed_history()
    status = client.get(f"/jobs/{PROMPT_ID}")

    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    jobs = client.get(f"/projects/{project['id']}").json()["jobs"]
    assert jobs[0]["status"] == "completed"
