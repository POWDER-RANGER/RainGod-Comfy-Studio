"""Tests for the CircuitBreaker and ComfyUIClient in comfyui_client.py."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from backend.comfyui_client import CircuitBreaker, CircuitState, ComfyUIClient
from backend.rain_backend_config import ComfyUIConfig


# ---------------------------------------------------------------------------
# CircuitBreaker unit tests
# ---------------------------------------------------------------------------

class TestCircuitBreakerInitialState:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_is_open_returns_false_when_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.is_open() is False


class TestCircuitBreakerFailures:
    def test_single_failure_stays_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_opens_at_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_is_open_returns_true_when_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.is_open() is True

    def test_success_resets_to_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        cb.record_success()
        # One more failure should NOT open (count was reset)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerHalfOpen:
    def test_transitions_to_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN

    def test_does_not_transition_before_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=3600.0)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN  # timeout far in the future


# ---------------------------------------------------------------------------
# ComfyUIClient unit tests
# ---------------------------------------------------------------------------

class TestComfyUIClientHealthCheck:
    def test_health_check_true_on_200(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999)
        client = ComfyUIClient(comfyui_config=cfg, max_retries=0)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client._session, "get", return_value=mock_resp):
            assert client.health_check() is True

    def test_health_check_false_on_connection_error(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999)
        client = ComfyUIClient(comfyui_config=cfg, max_retries=0)
        with patch.object(
            client._session, "get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            assert client.health_check() is False


class TestComfyUIClientQueuePrompt:
    def _make_mock_response(self, prompt_id: str) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"prompt_id": prompt_id}
        return resp

    def test_returns_prompt_id(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999)
        client = ComfyUIClient(comfyui_config=cfg, max_retries=0)
        mock_resp = self._make_mock_response("abc-123")
        with patch.object(client._session, "request", return_value=mock_resp):
            result = client.queue_prompt({"1": {"class_type": "Test", "inputs": {}}})
        assert result == "abc-123"

    def test_dedup_cache_returns_same_id(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999)
        client = ComfyUIClient(comfyui_config=cfg, max_retries=0)
        workflow = {"1": {"class_type": "Test", "inputs": {}}}
        mock_resp = self._make_mock_response("dedup-id")

        with patch.object(client._session, "request", return_value=mock_resp) as mock_req:
            id1 = client.queue_prompt(workflow, deduplicate=True)
            id2 = client.queue_prompt(workflow, deduplicate=True)

        assert id1 == id2 == "dedup-id"
        # HTTP request should only be made once (second call hits cache)
        assert mock_req.call_count == 1

    def test_dedup_disabled_sends_two_requests(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999)
        client = ComfyUIClient(comfyui_config=cfg, max_retries=0)
        workflow = {"1": {"class_type": "Test", "inputs": {}}}
        mock_resp = self._make_mock_response("no-dedup-id")

        with patch.object(client._session, "request", return_value=mock_resp) as mock_req:
            client.queue_prompt(workflow, deduplicate=False)
            client.queue_prompt(workflow, deduplicate=False)

        assert mock_req.call_count == 2

    def test_raises_when_circuit_open(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999)
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()  # open the circuit
        client = ComfyUIClient(comfyui_config=cfg, circuit_breaker=cb, max_retries=0)

        with pytest.raises(RuntimeError, match="circuit breaker is OPEN"):
            client.queue_prompt({})


class TestComfyUIClientRetry:
    def test_retries_on_connection_error(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999, timeout=1)
        client = ComfyUIClient(
            comfyui_config=cfg,
            max_retries=2,
            retry_delay_base=0.01,  # very fast for tests
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"prompt_id": "retry-id"}

        side_effects = [
            requests.exceptions.ConnectionError("fail 1"),
            requests.exceptions.ConnectionError("fail 2"),
            mock_resp,
        ]
        with patch.object(client._session, "request", side_effect=side_effects) as mock_req:
            result = client.queue_prompt({}, deduplicate=False)

        assert result == "retry-id"
        assert mock_req.call_count == 3  # 2 failures + 1 success

    def test_raises_after_max_retries_exceeded(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999, timeout=1)
        client = ComfyUIClient(
            comfyui_config=cfg,
            max_retries=1,
            retry_delay_base=0.01,
        )
        with patch.object(
            client._session,
            "request",
            side_effect=requests.exceptions.ConnectionError("always fails"),
        ):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.queue_prompt({}, deduplicate=False)


class TestComfyUIClientDedup:
    def test_clear_dedup_cache(self) -> None:
        cfg = ComfyUIConfig(host="127.0.0.1", port=19999)
        client = ComfyUIClient(comfyui_config=cfg, max_retries=0)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"prompt_id": "id-001"}

        workflow = {"node": "value"}
        with patch.object(client._session, "request", return_value=mock_resp):
            client.queue_prompt(workflow, deduplicate=True)

        assert len(client._dedup_cache) == 1
        client.clear_dedup_cache()
        assert len(client._dedup_cache) == 0

    def test_hash_workflow_is_deterministic(self) -> None:
        wf = {"a": 1, "b": {"c": 3}}
        h1 = ComfyUIClient._hash_workflow(wf)
        h2 = ComfyUIClient._hash_workflow(wf)
        assert h1 == h2

    def test_different_workflows_have_different_hashes(self) -> None:
        wf1 = {"seed": 1}
        wf2 = {"seed": 2}
        assert ComfyUIClient._hash_workflow(wf1) != ComfyUIClient._hash_workflow(wf2)
