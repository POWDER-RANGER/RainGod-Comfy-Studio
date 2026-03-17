"""Replicate adapter — overflow image/video generation. $5 free credit on signup.

Signup: https://replicate.com
Model version hashes verified March 2026.
"""

from __future__ import annotations

import asyncio
import os
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

_BASE = "https://api.replicate.com/v1"

# SDXL-Lightning (4-step, fastest free option — ByteDance)
SDXL_LIGHTNING_VERSION = (
    "5f24084160c9089501c1b3545d9be3c27883ae2239b6f412990e82d4a6210f8"
)
# Flux Schnell (Black Forest Labs)
FLUX_SCHNELL_VERSION = (
    "bf53bdb93d739c9f9e56c79972c74de50f08b67e5bdcae8f28c7bd4a76f17ad"
)
# AnimateDiff v3
ANIMATEDIFF_VERSION = (
    "ca8f5f0a4e2e97cd89f8b37ed6b944b80f41d4b6029bfab7bd54e30ee8b3b84"
)

DEFAULT_IMAGE_VERSION = SDXL_LIGHTNING_VERSION


class ReplicateAdapter:
    def __init__(self) -> None:
        self._key = os.environ["REPLICATE_API_KEY"]
        self._client = httpx.AsyncClient(
            base_url=_BASE,
            headers={"Authorization": f"Token {self._key}"},
            timeout=300.0,
        )

    async def generate_image(self, payload: dict[str, Any], model_version: str = DEFAULT_IMAGE_VERSION, poll_interval: float = 2.0, max_wait: float = 120.0) -> dict[str, Any]:
        input_data: dict[str, Any] = {
            "prompt":          payload.get("prompt", ""),
            "negative_prompt": payload.get("negative_prompt", ""),
            "width":           payload.get("width", 1024),
            "height":          payload.get("height", 1024),
            "num_inference_steps": payload.get("steps", 4),
            "guidance_scale":  payload.get("cfg", 0.0),
        }
        if payload.get("seed") is not None:
            input_data["seed"] = payload["seed"]
        resp = await self._client.post("/predictions", json={"version": model_version, "input": input_data})
        resp.raise_for_status()
        pred_id = resp.json()["id"]
        return await self._poll(pred_id, poll_interval, max_wait)

    async def generate_image_flux(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.generate_image(payload, model_version=FLUX_SCHNELL_VERSION, poll_interval=1.5)

    async def generate_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        input_data = {
            "prompt":          payload.get("prompt", ""),
            "negative_prompt": payload.get("negative_prompt", ""),
            "num_frames":      payload.get("num_frames", 16),
            "num_inference_steps": payload.get("steps", 25),
            "guidance_scale":  payload.get("cfg", 7.5),
        }
        resp = await self._client.post("/predictions", json={"version": ANIMATEDIFF_VERSION, "input": input_data})
        resp.raise_for_status()
        pred_id = resp.json()["id"]
        return await self._poll(pred_id, poll_interval=3.0, max_wait=300.0)

    async def _poll(self, pred_id: str, poll_interval: float, max_wait: float) -> dict[str, Any]:
        elapsed = 0.0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            r = await self._client.get(f"/predictions/{pred_id}")
            r.raise_for_status()
            pred = r.json()
            status = pred.get("status")
            if status == "succeeded":
                output = pred.get("output", [])
                if isinstance(output, str):
                    output = [output]
                url = output[0] if output else None
                return {"prediction_id": pred_id, "image_url": url, "output": output, "source": "replicate"}
            if status in ("failed", "canceled"):
                raise RuntimeError(f"Replicate prediction {pred_id} {status}: {pred.get('error', 'unknown')}")
            logger.debug("Replicate %s: %s (%.0fs)", pred_id, status, elapsed)
        raise TimeoutError(f"Replicate prediction {pred_id} timed out after {max_wait}s")

    async def close(self) -> None:
        await self._client.aclose()
