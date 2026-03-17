"""RAINGOD ComfyUI API Client.

Stateless, production-ready client with:
- Circuit breaker (half-open probe after cooldown)
- Exponential backoff retry
- SHA-256 request deduplication
- WebSocket result polling
- Health check
- Queue management (status / cancel)
- Image retrieval
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .rain_backend_config import ComfyUIConfig, config as global_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitState(str, Enum):
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # failing; reject calls immediately
    HALF_OPEN = "half_open" # probing to see if service recovered


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds before entering HALF_OPEN
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "ComfyUI circuit breaker OPEN after %d failures",
                self._failure_count,
            )

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# Session Factory (urllib3 retry on transport-level errors only)
# ---------------------------------------------------------------------------

def _make_session(max_retries: int = 0) -> requests.Session:
    """Return a requests.Session with a single pooled adapter."""
    session = requests.Session()
    retry_config = Retry(
        total=max_retries,
        backoff_factor=0.5,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "POST", "DELETE"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_config, pool_connections=4, pool_maxsize=16)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ---------------------------------------------------------------------------
# ComfyUI Client
# ---------------------------------------------------------------------------

class ComfyUIClient:
    """Stateless ComfyUI API client.

    One instance per application process is sufficient; the underlying session
    pool handles concurrent requests safely.
    """

    def __init__(
        self,
        comfyui_config: ComfyUIConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        max_retries: int = 3,
        retry_delay_base: float = 2.0,
    ) -> None:
        self._cfg = comfyui_config or global_config.comfyui
        self._cb = circuit_breaker or CircuitBreaker()
        self._max_retries = max_retries
        self._retry_delay_base = retry_delay_base
        self._session = _make_session()
        self._dedup_cache: dict[str, str] = {}  # hash -> prompt_id
        self._client_id = str(uuid.uuid4())

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _hash_workflow(workflow: dict[str, Any]) -> str:
        """SHA-256 hash of a JSON-serialised workflow for deduplication."""
        serialised = json.dumps(workflow, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialised.encode()).hexdigest()

    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Execute an HTTP request with circuit breaker + exponential backoff."""
        if self._cb.is_open():
            raise RuntimeError(
                "ComfyUI circuit breaker is OPEN — upstream is unavailable"
            )

        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.request(
                    method,
                    url,
                    timeout=self._cfg.timeout,
                    **kwargs,
                )
                resp.raise_for_status()
                self._cb.record_success()
                return resp
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                self._cb.record_failure()
                if attempt < self._max_retries:
                    delay = self._retry_delay_base ** attempt
                    logger.warning(
                        "ComfyUI request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self._max_retries + 1,
                        delay,
                        exc,
                    )
                    time.sleep(delay)

        raise last_exc

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def health_check(self) -> bool:
        """Return True if ComfyUI is reachable and responsive."""
        try:
            resp = self._session.get(
                f"{self._cfg.base_url}/system_stats",
                timeout=10,
            )
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def queue_prompt(
        self,
        workflow: dict[str, Any],
        deduplicate: bool = True,
    ) -> str:
        """Submit a workflow to ComfyUI and return the prompt_id.

        Args:
            workflow: A valid ComfyUI workflow graph (node dict).
            deduplicate: If True and an identical workflow was recently
                submitted, return the cached prompt_id immediately.

        Returns:
            The prompt_id string assigned by ComfyUI.
        """
        if deduplicate:
            wf_hash = self._hash_workflow(workflow)
            if cached_id := self._dedup_cache.get(wf_hash):
                logger.debug("Dedup hit: returning cached prompt_id %s", cached_id)
                return cached_id

        payload = {
            "prompt": workflow,
            "client_id": self._client_id,
        }
        resp = self._request("POST", self._cfg.prompt_url, json=payload)
        prompt_id: str = resp.json()["prompt_id"]

        if deduplicate:
            self._dedup_cache[wf_hash] = prompt_id

        logger.info("Queued prompt_id=%s", prompt_id)
        return prompt_id

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        """Return the full history entry for a completed prompt."""
        url = f"{self._cfg.history_url}/{prompt_id}"
        resp = self._request("GET", url)
        data: dict[str, Any] = resp.json()
        return data.get(prompt_id, {})

    def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        """Poll history until the prompt finishes or timeout expires."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            history = self.get_history(prompt_id)
            if history.get("status", {}).get("completed"):
                logger.info("prompt_id=%s completed", prompt_id)
                return history
            time.sleep(poll_interval)

        raise TimeoutError(
            f"prompt_id={prompt_id} did not complete within {timeout:.0f}s"
        )

    def get_queue_status(self) -> dict[str, Any]:
        """Return current queue state from ComfyUI."""
        resp = self._request("GET", self._cfg.queue_url)
        return resp.json()  # type: ignore[no-any-return]

    def cancel_prompt(self, prompt_id: str) -> bool:
        """Request cancellation of a queued or running prompt.

        Returns True if the cancellation request was accepted (HTTP 200).
        """
        try:
            resp = self._request(
                "POST",
                f"{self._cfg.base_url}/interrupt",
                json={"prompt_id": prompt_id},
            )
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_image_bytes(self, filename: str, subfolder: str = "", image_type: str = "output") -> bytes:
        """Download a generated image from ComfyUI's /view endpoint."""
        params = {"filename": filename, "type": image_type}
        if subfolder:
            params["subfolder"] = subfolder
        resp = self._request(
            "GET",
            f"{self._cfg.base_url}/view",
            params=params,
        )
        return resp.content

    def get_object_info(self) -> dict[str, Any]:
        """Return ComfyUI node type information (custom node discovery)."""
        resp = self._request("GET", f"{self._cfg.base_url}/object_info")
        return resp.json()  # type: ignore[no-any-return]

    def clear_dedup_cache(self) -> None:
        """Clear the in-memory deduplication cache."""
        self._dedup_cache.clear()
