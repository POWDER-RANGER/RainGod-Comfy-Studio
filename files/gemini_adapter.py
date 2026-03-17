"""Gemini Flash adapter — multimodal, long context, free tier."""

from __future__ import annotations
import base64, os, httpx, logging
from typing import Any

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiAdapter:
    def __init__(self) -> None:
        self._key = os.environ["GEMINI_API_KEY"]
        self._client = httpx.AsyncClient(timeout=60.0)
        self._model = "gemini-2.0-flash"

    async def generate(self, prompt: str, **kwargs) -> str:
        url = f"{_GEMINI_BASE}/models/{self._model}:generateContent?key={self._key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def vision(
        self,
        prompt: str,
        image_b64: str | None = None,
        image_url: str | None = None,
        mime_type: str = "image/png",
    ) -> str:
        parts: list[dict] = [{"text": prompt}]

        if image_url and not image_b64:
            async with httpx.AsyncClient(timeout=30) as fc:
                r = await fc.get(image_url)
                image_b64 = base64.b64encode(r.content).decode()

        if image_b64:
            parts.append({
                "inline_data": {"mime_type": mime_type, "data": image_b64}
            })

        url = f"{_GEMINI_BASE}/models/{self._model}:generateContent?key={self._key}"
        resp = await self._client.post(url, json={"contents": [{"parts": parts}]})
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def close(self) -> None:
        await self._client.aclose()
