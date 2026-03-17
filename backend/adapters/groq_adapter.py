"""Groq adapter — LPU inference, 14,400 req/day free tier."""

from __future__ import annotations

import os
import httpx
import logging

logger = logging.getLogger(__name__)

_GROQ_BASE = "https://api.groq.com/openai/v1"

DEFAULT_MODEL   = "llama-3.3-70b-versatile"
TOOL_USE_MODEL  = "llama3-groq-70b-8192-tool-use-preview"
REASONING_MODEL = "deepseek-r1-distill-llama-70b"
FAST_MODEL      = "llama-3.1-8b-instant"


class GroqAdapter:
    def __init__(self) -> None:
        self._key = os.environ["GROQ_API_KEY"]
        self._client = httpx.AsyncClient(
            base_url=_GROQ_BASE,
            headers={"Authorization": f"Bearer {self._key}"},
            timeout=60.0,
        )

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
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

    async def close(self) -> None:
        await self._client.aclose()
