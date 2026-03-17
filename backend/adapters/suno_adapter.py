"""Suno adapter — 50 songs/day free, full produced tracks with vocals."""

from __future__ import annotations

import asyncio
import os
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

_SUNO_BASE = "https://api.suno.ai/v1"


class SunoAdapter:
    def __init__(self) -> None:
        self._key = os.environ["SUNO_API_KEY"]
        self._client = httpx.AsyncClient(
            base_url=_SUNO_BASE,
            headers={"Authorization": f"Bearer {self._key}"},
            timeout=300.0,
        )

    async def generate(
        self,
        payload: dict[str, Any],
        poll_interval: float = 5.0,
        max_wait: float = 240.0,
    ) -> dict[str, Any]:
        submit_payload = {
            "prompt": payload.get("prompt", ""),
            "tags": payload.get("tags", ""),
            "title": payload.get("title", "RainGod Track"),
            "make_instrumental": payload.get("instrumental", False),
            "duration": payload.get("duration", 30),
        }
        resp = await self._client.post("/generate", json=submit_payload)
        resp.raise_for_status()
        clip_ids = [c["id"] for c in resp.json().get("clips", [])]
        if not clip_ids:
            raise RuntimeError("Suno returned no clip IDs")
        clip_id = clip_ids[0]
        elapsed = 0.0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            status_resp = await self._client.get(f"/clips/{clip_id}")
            status_resp.raise_for_status()
            clip = status_resp.json()
            if clip.get("status") == "complete":
                return {
                    "clip_id":   clip["id"],
                    "title":     clip.get("title"),
                    "audio_url": clip.get("audio_url"),
                    "image_url": clip.get("image_url"),
                    "duration":  clip.get("duration"),
                    "tags":      clip.get("tags"),
                }
            logger.debug("Suno clip %s status: %s", clip_id, clip.get("status"))
        raise TimeoutError(f"Suno clip {clip_id} did not complete within {max_wait}s")

    async def close(self) -> None:
        await self._client.aclose()
