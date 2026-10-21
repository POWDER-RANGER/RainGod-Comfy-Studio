"""Integration checks for the combined application lifecycle and route ownership."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


def test_main_app_starts_and_closes_backend_and_preserves_main_routes(
    monkeypatch, tmp_path
) -> None:
    import backend.dispatcher as dispatcher_module
    import backend.main as main
    import backend.rain_backend as rain_backend

    previous_client = rain_backend.client
    monkeypatch.setattr(rain_backend, "client", previous_client)
    monkeypatch.setattr(rain_backend, "OUTPUT_DIR", tmp_path)

    comfy_client = MagicMock()
    comfy_client.queue_prompt.return_value = "prompt-123"
    monkeypatch.setattr(rain_backend, "ComfyUIClient", lambda: comfy_client)

    dispatcher = MagicMock()
    dispatcher.status.return_value = {"local_ollama": False}
    dispatcher.close = AsyncMock()
    monkeypatch.setattr(dispatcher_module, "RainGodDispatcher", lambda: dispatcher)

    with TestClient(main.app) as http:
        assert rain_backend.client is comfy_client

        root = http.get("/")
        assert root.status_code == 200
        assert root.headers["content-type"].startswith("text/html")

        health = http.get("/health")
        assert health.status_code == 200
        assert health.json() == {
            "status": "ok",
            "adapters": {"local_ollama": False},
        }

        generated = http.post(
            "/generate",
            json={"prompt": "rainy neon street"},
        )
        assert generated.status_code == 202
        assert generated.json()["prompt_id"] == "prompt-123"

    assert rain_backend.client is None
    comfy_client.close.assert_called_once_with()
    dispatcher.close.assert_awaited_once_with()
