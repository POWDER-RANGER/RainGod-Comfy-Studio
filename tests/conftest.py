"""Pytest fixtures shared across the RAINGOD test suite.

All environment variables that affect module-level config must be set
*before* any backend module is imported.  This conftest.py is the correct
place to do that.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Environment setup — must happen before any backend module is imported so
# CORS middleware and the config singleton see the correct test values.
# ---------------------------------------------------------------------------
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("COMFYUI_HOST", "127.0.0.1")
os.environ.setdefault("COMFYUI_PORT", "18188")  # port unlikely to be in use


def _make_mock_comfyui_client() -> MagicMock:
    """Return a MagicMock that looks like a live ComfyUIClient."""
    m = MagicMock()
    m.health_check.return_value = True
    m.queue_prompt.return_value = "test-prompt-id-abc123"
    m.get_queue_status.return_value = {
        "queue_running": [],
        "queue_pending": [],
    }
    m.cancel_prompt.return_value = True
    return m


@pytest.fixture(scope="session")
def app():
    """Return the FastAPI application with the ComfyUI client pre-injected.

    The TestClient context manager triggers startup/shutdown lifespan events.
    We launch the app inside a TestClient block so startup runs, then we
    immediately replace the module-level ``client`` singleton with our mock
    before any test makes a request.
    """
    import backend.rain_backend as mod
    from backend.rain_backend import app as _app

    with TestClient(_app) as _tc:
        mod.client = _make_mock_comfyui_client()
        yield _app


@pytest.fixture(scope="session")
def client(app) -> TestClient:
    """Return a session-scoped synchronous TestClient."""
    import backend.rain_backend as mod
    tc = TestClient(app)
    mod.client = _make_mock_comfyui_client()
    return tc


@pytest.fixture()
def tmp_workflows_dir(tmp_path: Path) -> Path:
    """Return a temporary directory pre-seeded with a minimal workflow JSON."""
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "test.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "test positive", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "test negative", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                "latent_image": ["4", 0], "seed": 0, "steps": 20, "cfg": 7.0,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "test"}},
    }
    (tmp_path / "test_workflow.json").write_text(json.dumps(wf))
    return tmp_path


@pytest.fixture()
def tmp_lora_dir(tmp_path: Path) -> Path:
    """Return a temporary loras/ directory with dummy LoRA files.

    Contents:
    - ``custom_style_v1.safetensors``  — NOT in LORA_MAPPINGS, will be discovered
    - ``brand_new_extra.safetensors``  — NOT in LORA_MAPPINGS, will be discovered
    - ``ignored.txt``                  — ignored (wrong extension)

    We deliberately do NOT include files that match existing LORA_MAPPINGS
    filenames so that de-duplication logic is separately verifiable.
    """
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    (lora_dir / "custom_style_v1.safetensors").write_bytes(b"\x00" * 200)
    (lora_dir / "brand_new_extra.safetensors").write_bytes(b"\x00" * 150)
    (lora_dir / "ignored.txt").write_text("not a lora")
    return lora_dir
