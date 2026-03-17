"""Tests for the FastAPI endpoints in rain_backend.py.

Covers:
- GET  /
- GET  /health
- GET  /config
- GET  /presets
- POST /generate  (valid, invalid preset, invalid resolution)
- POST /batch-generate
- GET  /queue/status
- DEL  /queue/{prompt_id}
- GET  /outputs/{filename}  (404 path, path-traversal attempt)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot:
    def test_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_has_name_and_version(self, client):
        body = r = client.get("/").json()
        assert "name" in body
        assert "version" in body
        assert body["docs"] == "/docs"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("healthy", "degraded")
        assert isinstance(data["comfyui_available"], bool)
        assert "uptime_seconds" in data
        assert "gpu_tier" in data

    def test_health_degraded_when_comfyui_down(self, app, client):
        """When ComfyUI health check returns False, status should be 'degraded'."""
        import backend.rain_backend as mod
        original_hc = mod.client.health_check.return_value
        mod.client.health_check.return_value = False
        try:
            r = client.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "degraded"
        finally:
            mod.client.health_check.return_value = original_hc


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_returns_expected_keys(self, client):
        r = client.get("/config")
        assert r.status_code == 200
        body = r.json()
        for key in ("comfyui_url", "gpu_tier", "resolution_presets", "sampler_presets", "lora_styles"):
            assert key in body, f"Missing key: {key}"

    def test_resolution_presets_is_list(self, client):
        body = client.get("/config").json()
        assert isinstance(body["resolution_presets"], list)
        assert len(body["resolution_presets"]) > 0


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

class TestPresets:
    def test_returns_200(self, client):
        r = client.get("/presets")
        assert r.status_code == 200

    def test_required_top_level_keys(self, client):
        body = client.get("/presets").json()
        assert {"resolution", "samplers", "lora", "quality_tiers"} <= body.keys()

    def test_sampler_presets_have_required_fields(self, client):
        samplers = client.get("/presets").json()["samplers"]
        for name, preset in samplers.items():
            for field in ("steps", "cfg", "sampler_name", "scheduler"):
                assert field in preset, f"Sampler '{name}' missing field '{field}'"

    def test_resolution_presets_have_width_height(self, client):
        resolutions = client.get("/presets").json()["resolution"]
        for name, res in resolutions.items():
            assert "width" in res and "height" in res, f"Resolution '{name}' missing dimensions"

    def test_lora_presets_have_required_fields(self, client):
        loras = client.get("/presets").json()["lora"]
        for name, lora in loras.items():
            for field in ("filename", "strength_model"):
                assert field in lora, f"LoRA '{name}' missing field '{field}'"


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

class TestGenerate:
    _VALID_PAYLOAD = {
        "prompt": "glowing neon city at night, synthwave aesthetic",
        "negative_prompt": "blurry, low quality",
        "preset": "quality",
        "resolution": "cover_art",
    }

    def test_valid_request_returns_202(self, client):
        r = client.post("/generate", json=self._VALID_PAYLOAD)
        assert r.status_code == 202

    def test_response_has_required_fields(self, client):
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        for field in ("prompt_id", "job_id", "status", "estimated_time",
                      "preset_used", "resolution_used"):
            assert field in body, f"Response missing field '{field}'"

    def test_status_is_queued(self, client):
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        assert body["status"] == "queued"

    def test_prompt_id_matches_mock(self, client):
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        assert body["prompt_id"] == "test-prompt-id-abc123"

    def test_invalid_preset_returns_400(self, client):
        payload = {**self._VALID_PAYLOAD, "preset": "nonexistent_preset"}
        r = client.post("/generate", json=payload)
        assert r.status_code == 400
        assert "preset" in r.json()["detail"].lower()

    def test_invalid_resolution_returns_400(self, client):
        payload = {**self._VALID_PAYLOAD, "resolution": "nonexistent_resolution"}
        r = client.post("/generate", json=payload)
        assert r.status_code == 400
        assert "resolution" in r.json()["detail"].lower()

    def test_empty_prompt_returns_422(self, client):
        r = client.post("/generate", json={**self._VALID_PAYLOAD, "prompt": ""})
        assert r.status_code == 422

    def test_optional_seed_is_forwarded_in_metadata(self, client):
        payload = {**self._VALID_PAYLOAD, "seed": 42}
        body = client.post("/generate", json=payload).json()
        assert body["metadata"]["seed"] == 42

    def test_with_valid_lora_style(self, client):
        payload = {**self._VALID_PAYLOAD, "lora_style": "synthwave"}
        r = client.post("/generate", json=payload)
        assert r.status_code == 202

    def test_with_all_resolution_presets(self, client):
        from backend.rain_backend_config import RESOLUTION_PRESETS
        for res_key in RESOLUTION_PRESETS:
            payload = {**self._VALID_PAYLOAD, "resolution": res_key}
            r = client.post("/generate", json=payload)
            assert r.status_code == 202, f"Failed for resolution '{res_key}'"

    def test_with_all_sampler_presets(self, client):
        from backend.rain_backend_config import SAMPLER_PRESETS
        for preset_key in SAMPLER_PRESETS:
            payload = {**self._VALID_PAYLOAD, "preset": preset_key}
            r = client.post("/generate", json=payload)
            assert r.status_code == 202, f"Failed for preset '{preset_key}'"


# ---------------------------------------------------------------------------
# Batch Generate
# ---------------------------------------------------------------------------

class TestBatchGenerate:
    _BASE_REQ = {
        "prompt": "abstract album art",
        "preset": "fast",
        "resolution": "thumbnail",
    }

    def test_valid_batch_returns_202(self, client):
        payload = {"requests": [self._BASE_REQ, self._BASE_REQ]}
        r = client.post("/batch-generate", json=payload)
        assert r.status_code == 202

    def test_batch_response_fields(self, client):
        payload = {"requests": [self._BASE_REQ]}
        body = client.post("/batch-generate", json=payload).json()
        for field in ("batch_id", "total", "queued", "errors", "results"):
            assert field in body

    def test_batch_all_queued(self, client):
        n = 3
        payload = {"requests": [self._BASE_REQ] * n}
        body = client.post("/batch-generate", json=payload).json()
        assert body["total"] == n
        assert body["queued"] == n
        assert body["errors"] == 0

    def test_empty_batch_returns_422(self, client):
        r = client.post("/batch-generate", json={"requests": []})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Queue Status
# ---------------------------------------------------------------------------

class TestQueueStatus:
    def test_returns_200(self, client):
        r = client.get("/queue/status")
        assert r.status_code == 200

    def test_has_queue_keys(self, client):
        body = r = client.get("/queue/status").json()
        assert "queue_running" in body or "queue_pending" in body


# ---------------------------------------------------------------------------
# Queue Cancel
# ---------------------------------------------------------------------------

class TestQueueCancel:
    def test_cancel_returns_cancelled_true(self, client):
        r = client.delete("/queue/test-prompt-id-abc123")
        assert r.status_code == 200
        body = r.json()
        assert body["cancelled"] is True
        assert body["prompt_id"] == "test-prompt-id-abc123"


# ---------------------------------------------------------------------------
# Outputs endpoint
# ---------------------------------------------------------------------------

class TestOutputs:
    def test_missing_file_returns_404(self, client):
        r = client.get("/outputs/does_not_exist.png")
        assert r.status_code == 404

    def test_path_traversal_blocked(self, client, tmp_path):
        """Ensure ../secret patterns cannot escape the outputs directory."""
        r = client.get("/outputs/..%2F..%2Fetc%2Fpasswd")
        # Should be 400 (validation) or 404, never 200
        assert r.status_code in (400, 404, 422)

    def test_valid_file_served(self, client, tmp_path, monkeypatch):
        """A file that exists in the outputs dir should be served."""
        from pathlib import Path
        import backend.rain_backend as mod

        # Temporarily redirect OUTPUT_DIR to a temp directory
        original_dir = mod.OUTPUT_DIR
        test_output_dir = tmp_path / "outputs"
        test_output_dir.mkdir()
        test_file = test_output_dir / "test_image.png"
        # Write a minimal 1×1 PNG (89 bytes)
        test_file.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        monkeypatch.setattr(mod, "OUTPUT_DIR", test_output_dir)

        r = client.get("/outputs/test_image.png")
        assert r.status_code == 200

        monkeypatch.setattr(mod, "OUTPUT_DIR", original_dir)


# ---------------------------------------------------------------------------
# Helper import alias to avoid circular fixture issues
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient as TestClientImport
