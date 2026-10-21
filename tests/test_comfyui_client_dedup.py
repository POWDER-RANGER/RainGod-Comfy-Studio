"""Regression tests for ComfyUI workflow submission semantics."""

from __future__ import annotations

from typing import Any

from backend.comfyui_client import ComfyUIClient
from backend.rain_backend_config import ComfyUIConfig


class _Response:
    def __init__(self, prompt_id: str) -> None:
        self._prompt_id = prompt_id

    def json(self) -> dict[str, str]:
        return {"prompt_id": self._prompt_id}


def _client_with_recording_request() -> tuple[ComfyUIClient, list[dict[str, Any]]]:
    client = ComfyUIClient(
        comfyui_config=ComfyUIConfig(host="127.0.0.1", port=8188),
        max_retries=0,
    )
    submitted: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> _Response:
        submitted.append({"method": method, "url": url, **kwargs})
        return _Response(f"prompt-{len(submitted)}")

    client._request = fake_request  # type: ignore[method-assign]
    return client, submitted


def test_identical_workflows_are_submitted_as_new_jobs_by_default() -> None:
    client, submitted = _client_with_recording_request()
    workflow = {"1": {"class_type": "SaveImage", "inputs": {"filename_prefix": "rain"}}}

    first = client.queue_prompt(workflow)
    second = client.queue_prompt(workflow)

    assert first == "prompt-1"
    assert second == "prompt-2"
    assert len(submitted) == 2


def test_opt_in_deduplication_reuses_cached_prompt_id() -> None:
    client, submitted = _client_with_recording_request()
    workflow = {"1": {"class_type": "SaveImage", "inputs": {"filename_prefix": "rain"}}}

    first = client.queue_prompt(workflow, deduplicate=True)
    second = client.queue_prompt(workflow, deduplicate=True)

    assert first == "prompt-1"
    assert second == first
    assert len(submitted) == 1


def test_clearing_deduplication_cache_allows_resubmission() -> None:
    client, submitted = _client_with_recording_request()
    workflow = {"1": {"class_type": "SaveImage", "inputs": {"filename_prefix": "rain"}}}

    first = client.queue_prompt(workflow, deduplicate=True)
    client.clear_dedup_cache()
    second = client.queue_prompt(workflow, deduplicate=True)

    assert first == "prompt-1"
    assert second == "prompt-2"
    assert len(submitted) == 2
