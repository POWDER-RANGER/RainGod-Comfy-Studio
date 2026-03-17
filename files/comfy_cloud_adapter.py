"""Comfy Cloud adapter — RTX Pro 6000, 96GB VRAM, 400 credits/month free.

Signup: https://comfy.org
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
import logging

logger = logging.getLogger(__name__)

_BASE = "https://api.comfy.org/v1"


class ComfyCloudAdapter:
    """Submit ComfyUI workflow JSON to Comfy Cloud, poll for output images."""

    def __init__(self) -> None:
        self._key = os.environ["COMFY_API_KEY"]
        self._client = httpx.AsyncClient(
            base_url=_BASE,
            headers={"Authorization": f"Bearer {self._key}"},
            timeout=300.0,
        )

    async def generate(
        self,
        payload: dict[str, Any],
        poll_interval: float = 3.0,
        max_wait: float = 300.0,
    ) -> dict[str, Any]:
        workflow = payload.get("workflow") or _build_sdxl_workflow(payload)
        resp = await self._client.post("/runs", json={"workflow": workflow})
        resp.raise_for_status()
        run_id = resp.json()["run_id"]
        return await self._poll(run_id, poll_interval, max_wait)

    async def generate_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        from ..workflows import ANIMATEDIFF_WORKFLOW
        wf = payload.get("workflow") or _patch_animatediff(ANIMATEDIFF_WORKFLOW, payload)
        return await self.generate({"workflow": wf})

    async def _poll(self, run_id: str, interval: float, max_wait: float) -> dict:
        elapsed = 0.0
        while elapsed < max_wait:
            await asyncio.sleep(interval)
            elapsed += interval
            r = await self._client.get(f"/runs/{run_id}")
            r.raise_for_status()
            run = r.json()
            status = run.get("status")
            if status == "completed":
                urls = []
                for node_out in run.get("outputs", {}).values():
                    for img in node_out.get("images", []):
                        urls.append(img.get("url"))
                return {"run_id": run_id, "image_urls": urls,
                        "image_url": urls[0] if urls else None}
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"Comfy Cloud run {run_id} {status}: {run.get('error')}")
            logger.debug("Comfy Cloud run %s: %s (%.0fs)", run_id, status, elapsed)
        raise TimeoutError(f"Comfy Cloud run {run_id} timed out after {max_wait}s")

    async def close(self) -> None:
        await self._client.aclose()


def _build_sdxl_workflow(p: dict) -> dict:
    """Minimal SDXL txt2img workflow — used when no explicit workflow supplied."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": p.get("checkpoint", "sd_xl_base_1.0.safetensors")}},
        "2": {"class_type": "CLIPTextEncode",
              "inputs": {"text": p.get("prompt", ""), "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"text": p.get("negative_prompt", ""), "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": p.get("width", 1024),
                         "height": p.get("height", 1024),
                         "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0], "seed": p.get("seed", 0),
                         "steps": p.get("steps", 20), "cfg": p.get("cfg", 7.0),
                         "sampler_name": "euler_ancestral", "scheduler": "normal",
                         "denoise": 1.0}},
        "6": {"class_type": "VAEDecode",
              "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": "raingod"}},
    }


def _patch_animatediff(wf: dict, p: dict) -> dict:
    """Patch AnimateDiff template with runtime values."""
    import copy, uuid
    wf = copy.deepcopy(wf)
    # Node "2" = positive CLIP, "3" = negative, "5" = seed
    if "2" in wf:
        wf["2"]["inputs"]["text"] = p.get("prompt", "")
    if "3" in wf:
        wf["3"]["inputs"]["text"] = p.get("negative_prompt", "")
    if "5" in wf:
        wf["5"]["inputs"]["seed"] = p.get("seed", int(uuid.uuid4().int % 2**32))
    return wf
