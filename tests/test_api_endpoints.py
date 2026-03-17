"""Tests for RAINGOD FastAPI endpoint behaviour.

All tests use a mocked ComfyUIClient so no real ComfyUI process is required.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestRoot:
    def test_returns_200(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200

    def test_body_contains_expected_keys(self, client: TestClient) -> None:
        body = client.get("/").json()
        assert "name" in body
        assert "version" in body
        assert "docs" in body
        assert "health" in body

    def test_version_is_string(self, client: TestClient) -> None:
        body = client.get("/").json()
        assert isinstance(body["version"], str)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200

    def test_backend_status_present(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")

    def test_comfyui_available_field(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert "comfyui_available" in body
        assert isinstance(body["comfyui_available"], bool)

    def test_gpu_tier_field(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert "gpu_tier" in body
        assert body["gpu_tier"] in ("cpu", "low_vram", "mid_vram", "high_vram")

    def test_uptime_is_non_negative(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert body["uptime_seconds"] >= 0.0


# ---------------------------------------------------------------------------
# GET /config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/config").status_code == 200

    def test_resolution_presets_present(self, client: TestClient) -> None:
        body = client.get("/config").json()
        assert "resolution_presets" in body
        assert len(body["resolution_presets"]) > 0

    def test_sampler_presets_present(self, client: TestClient) -> None:
        body = client.get("/config").json()
        assert "sampler_presets" in body

    def test_lora_styles_present(self, client: TestClient) -> None:
        body = client.get("/config").json()
        assert "lora_styles" in body


# ---------------------------------------------------------------------------
# GET /presets
# ---------------------------------------------------------------------------

class TestPresets:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/presets").status_code == 200

    def test_resolution_key(self, client: TestClient) -> None:
        body = client.get("/presets").json()
        assert "resolution" in body
        # cover_art is the default; must exist
        assert "cover_art" in body["resolution"]

    def test_samplers_key(self, client: TestClient) -> None:
        body = client.get("/presets").json()
        assert "samplers" in body
        # quality is the default sampler preset
        assert "quality" in body["samplers"]

    def test_sampler_has_required_fields(self, client: TestClient) -> None:
        samplers = client.get("/presets").json()["samplers"]
        for key, sampler in samplers.items():
            assert "steps" in sampler, f"Missing 'steps' in sampler {key!r}"
            assert "cfg" in sampler, f"Missing 'cfg' in sampler {key!r}"
            assert "sampler_name" in sampler

    def test_lora_key(self, client: TestClient) -> None:
        body = client.get("/presets").json()
        assert "lora" in body

    def test_quality_tiers_key(self, client: TestClient) -> None:
        body = client.get("/presets").json()
        assert "quality_tiers" in body
        assert "standard" in body["quality_tiers"]


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------

class TestGenerate:
    _VALID_PAYLOAD = {
        "prompt": "neon synthwave cityscape at dusk",
        "negative_prompt": "blurry, low quality",
        "preset": "quality",
        "resolution": "cover_art",
    }

    def test_returns_202(self, client: TestClient) -> None:
        r = client.post("/generate", json=self._VALID_PAYLOAD)
        assert r.status_code == 202

    def test_response_has_prompt_id(self, client: TestClient) -> None:
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        assert "prompt_id" in body
        assert isinstance(body["prompt_id"], str)

    def test_response_has_job_id(self, client: TestClient) -> None:
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        assert "job_id" in body

    def test_response_status_queued(self, client: TestClient) -> None:
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        assert body["status"] == "queued"

    def test_response_preset_used(self, client: TestClient) -> None:
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        assert body["preset_used"] == "quality"

    def test_response_resolution_used(self, client: TestClient) -> None:
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        res = body["resolution_used"]
        assert res["width"] == 1024
        assert res["height"] == 1024

    def test_seed_injected_into_metadata(self, client: TestClient) -> None:
        body = client.post("/generate", json=self._VALID_PAYLOAD).json()
        assert "seed" in body["metadata"]
        assert isinstance(body["metadata"]["seed"], int)

    def test_explicit_seed_is_respected(self, client: TestClient) -> None:
        payload = {**self._VALID_PAYLOAD, "seed": 12345}
        body = client.post("/generate", json=payload).json()
        assert body["metadata"]["seed"] == 12345

    def test_invalid_preset_returns_400(self, client: TestClient) -> None:
        payload = {**self._VALID_PAYLOAD, "preset": "nonexistent_preset"}
        r = client.post("/generate", json=payload)
        assert r.status_code == 400
        assert "nonexistent_preset" in r.json()["detail"]

    def test_invalid_resolution_returns_400(self, client: TestClient) -> None:
        payload = {**self._VALID_PAYLOAD, "resolution": "bad_resolution"}
        r = client.post("/generate", json=payload)
        assert r.status_code == 400

    def test_empty_prompt_returns_422(self, client: TestClient) -> None:
        payload = {**self._VALID_PAYLOAD, "prompt": ""}
        r = client.post("/generate", json=payload)
        assert r.status_code == 422

    def test_missing_prompt_returns_422(self, client: TestClient) -> None:
        r = client.post("/generate", json={"preset": "quality"})
        assert r.status_code == 422

    def test_lora_style_is_accepted(self, client: TestClient) -> None:
        payload = {**self._VALID_PAYLOAD, "lora_style": "synthwave"}
        r = client.post("/generate", json=payload)
        assert r.status_code == 202

    def test_unknown_lora_is_silently_ignored(self, client: TestClient) -> None:
        # Unknown LoRA should NOT cause an error — it is simply not applied
        payload = {**self._VALID_PAYLOAD, "lora_style": "does_not_exist"}
        r = client.post("/generate", json=payload)
        assert r.status_code == 202

    def test_all_sampler_presets_accepted(self, client: TestClient) -> None:
        from backend.rain_backend_config import SAMPLER_PRESETS
        for preset_name in SAMPLER_PRESETS:
            payload = {**self._VALID_PAYLOAD, "preset": preset_name}
            r = client.post("/generate", json=payload)
            assert r.status_code == 202, f"Preset {preset_name!r} returned {r.status_code}"

    def test_all_resolution_presets_accepted(self, client: TestClient) -> None:
        from backend.rain_backend_config import RESOLUTION_PRESETS
        for res_name in RESOLUTION_PRESETS:
            payload = {**self._VALID_PAYLOAD, "resolution": res_name}
            r = client.post("/generate", json=payload)
            assert r.status_code == 202, f"Resolution {res_name!r} returned {r.status_code}"


# ---------------------------------------------------------------------------
# POST /batch-generate
# ---------------------------------------------------------------------------

class TestBatchGenerate:
    _SINGLE = {
        "prompt": "abstract neon art",
        "preset": "fast",
        "resolution": "thumbnail",
    }

    def test_returns_202(self, client: TestClient) -> None:
        r = client.post("/batch-generate", json={"requests": [self._SINGLE]})
        assert r.status_code == 202

    def test_batch_id_present(self, client: TestClient) -> None:
        body = client.post("/batch-generate", json={"requests": [self._SINGLE]}).json()
        assert "batch_id" in body

    def test_total_count_correct(self, client: TestClient) -> None:
        payload = {"requests": [self._SINGLE, self._SINGLE]}
        body = client.post("/batch-generate", json=payload).json()
        assert body["total"] == 2

    def test_queued_count_correct(self, client: TestClient) -> None:
        payload = {"requests": [self._SINGLE]}
        body = client.post("/batch-generate", json=payload).json()
        assert body["queued"] == 1
        assert body["errors"] == 0

    def test_empty_requests_returns_422(self, client: TestClient) -> None:
        r = client.post("/batch-generate", json={"requests": []})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /queue/status
# ---------------------------------------------------------------------------

class TestQueueStatus:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/queue/status").status_code == 200

    def test_has_queue_keys(self, client: TestClient) -> None:
        body = client.get("/queue/status").json()
        assert "queue_running" in body
        assert "queue_pending" in body


# ---------------------------------------------------------------------------
# DELETE /queue/{prompt_id}
# ---------------------------------------------------------------------------

class TestCancelQueue:
    def test_cancel_returns_200(self, client: TestClient) -> None:
        r = client.delete("/queue/some-prompt-id")
        assert r.status_code == 200

    def test_response_has_cancelled_field(self, client: TestClient) -> None:
        body = client.delete("/queue/some-prompt-id").json()
        assert "cancelled" in body
        assert isinstance(body["cancelled"], bool)

    def test_response_echoes_prompt_id(self, client: TestClient) -> None:
        body = client.delete("/queue/my-test-id").json()
        assert body["prompt_id"] == "my-test-id"


# ---------------------------------------------------------------------------
# GET /outputs/{filename}
# ---------------------------------------------------------------------------

class TestOutputsEndpoint:
    def test_missing_file_returns_404(self, client: TestClient) -> None:
        r = client.get("/outputs/does_not_exist.png")
        assert r.status_code == 404

    def test_path_traversal_attempt_rejected(self, client: TestClient) -> None:
        # FastAPI's Path validator rejects literal slashes in path segments
        r = client.get("/outputs/../../etc/passwd")
        # Should be 404 (file not found) or 422 (validation) or 403 (forbidden)
        assert r.status_code in (400, 403, 404, 422)
