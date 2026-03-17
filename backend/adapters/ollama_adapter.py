"""Ollama local adapter — wraps the REST API exposed by ollama serve."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_OPTIONS = {
    "num_ctx": 4096,
    "temperature": 0.7,
    "top_p": 0.9,
}


class OllamaAdapter:
    """Async adapter for local Ollama inference.

    Models available on your stack:
      dolphin-llama3:8b   — uncensored general / agent
      qwen3:4b            — tool-use / structured JSON
      deepseek-r1:1.5b    — chain-of-thought reasoning
      moondream:1.8b      — vision (image → text)
      nomic-embed-text    — text embeddings / RAG
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def generate(
        self,
        prompt: str,
        model: str = "dolphin-llama3:8b",
        system: str | None = None,
        format: str | None = None,
        options: dict | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {**_DEFAULT_OPTIONS, **(options or {})},
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format
        resp = await self._client.post(f"{self._base}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["response"]

    async def chat(self, messages: list[dict], model: str = "dolphin-llama3:8b", system: str | None = None) -> str:
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False, "options": _DEFAULT_OPTIONS}
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + messages
        resp = await self._client.post(f"{self._base}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    async def vision(self, image_url: str, prompt: str = "Describe this image.", model: str = "moondream:1.8b") -> str:
        async with httpx.AsyncClient(timeout=30) as fc:
            img_resp = await fc.get(image_url)
            img_resp.raise_for_status()
        import base64
        img_b64 = base64.b64encode(img_resp.content).decode()
        payload = {"model": model, "prompt": prompt, "images": [img_b64], "stream": False}
        resp = await self._client.post(f"{self._base}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["response"]

    async def embed(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        resp = await self._client.post(f"{self._base}/api/embed", json={"model": model, "input": text})
        resp.raise_for_status()
        return resp.json().get("embeddings", [[]])[0]

    async def health(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        resp = await self._client.get(f"{self._base}/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    async def close(self) -> None:
        await self._client.aclose()
