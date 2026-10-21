"""Tests for real ComfyUI job-status and generated-image proxy endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


PROMPT_ID = "11111111-1111-4111-8111-111111111111"


def _completed_history() -> dict:
    return {
        "status": {"status_str": "success", "completed": True},
        "outputs": {
            "7": {
                "images": [
                    {"filename": "raingod_00001.png", "subfolder": "", "type": "output"}
                ]
            }
        },
    }


def _install_client(monkeypatch, *, history=None, queue=None, image_bytes=b"png-bytes"):
    import backend.rain_backend as backend

    fake = MagicMock()
    fake.get_history.return_value = history if history is not None else {}
    fake.get_queue_status.return_value = queue or {
        "queue_running": [],
        "queue_pending": [],
    }
    fake.get_image_bytes.return_value = image_bytes
    monkeypatch.setattr(backend, "client", fake)
    return fake


def test_job_status_reports_queued_prompt(client: TestClient, monkeypatch) -> None:
    _install_client(
        monkeypatch,
        queue={"queue_running": [], "queue_pending": [[1, PROMPT_ID, {}, {}, []]]},
    )

    response = client.get(f"/jobs/{PROMPT_ID}")

    assert response.status_code == 200
    assert response.json() == {
        "prompt_id": PROMPT_ID,
        "status": "queued",
        "completed": False,
        "images": [],
    }


def test_completed_job_exposes_image_url_from_history(client: TestClient, monkeypatch) -> None:
    _install_client(monkeypatch, history=_completed_history())

    response = client.get(f"/jobs/{PROMPT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["completed"] is True
    assert body["images"] == [{"index": 0, "url": f"/jobs/{PROMPT_ID}/images/0"}]


def test_job_image_is_retrieved_from_comfyui(client: TestClient, monkeypatch) -> None:
    fake = _install_client(monkeypatch, history=_completed_history(), image_bytes=b"real-image-bytes")

    response = client.get(f"/jobs/{PROMPT_ID}/images/0")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"real-image-bytes"
    fake.get_image_bytes.assert_called_once_with(
        "raingod_00001.png",
        subfolder="",
        image_type="output",
    )


def test_unknown_job_is_not_reported_as_success(client: TestClient, monkeypatch) -> None:
    _install_client(monkeypatch)

    response = client.get(f"/jobs/{PROMPT_ID}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_upstream_history_failure_returns_service_unavailable(
    client: TestClient, monkeypatch
) -> None:
    fake = _install_client(monkeypatch)
    fake.get_history.side_effect = RuntimeError("upstream unavailable")

    response = client.get(f"/jobs/{PROMPT_ID}")

    assert response.status_code == 503
    assert "history" in response.json()["detail"].lower()
