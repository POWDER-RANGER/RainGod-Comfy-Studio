"""OpenRouter adapter — 300+ models, many with :free suffix.

Signup: https://openrouter.ai
Free models (as of 2026): append :free to model ID, e.g. meta-llama/llama-3.3-70b-instruct:free
"""

from __future__ import annotations

import os
import httpx
import logging

logger = logging.getLogger(__name__)

_BASE = "https://openrouter.ai/api/v1"

FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "microsoft/phi-3-medium-128k-instruct:free",
]


class OpenRouterAdapter:
    """Fallback LLM — 300+ models, zero cost on :free tier."""

    def __init__(self) -> None:
        self._key = os.environ["OPENROUTER_API_KEY"]
        self._client = httpx.AsyncClient(
            base_url=_BASE,
            headers={
                "Authorization": f"Bearer {self._key}",
                "HTTP-Referer": "https://github.com/POWDER-RANGER/raingod-comfy-studio",
                "X-Title": "RainGod Comfy Studio",
            },
            timeout=90.0,
        )

    async def generate(
        self,
        prompt: str,
        model: str = FREE_MODELS[0],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.post("/chat/completions", json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def models(self) -> list[dict]:
        """List available models (cached by OpenRouter)."""
        resp = await self._client.get("/models")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def close(self) -> None:
        await self._client.aclose()
