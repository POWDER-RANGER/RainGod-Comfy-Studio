"""Comfy Cloud adapter — RTX Pro 6000, 96GB VRAM, 400 credits/month free."""

from __future__ import annotations
import asyncio, os, httpx, logging
from typing import Any

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
        """Submit a workflow or prompt dict, return image URLs."""
        # If payload has a 'workflow' key it's a full graph; otherwise build minimal
        workflow = payload.get("workflow") or _build_minimal_sdxl_workflow(payload)

        resp = await self._client.post("/runs", json={"workflow": workflow})
        resp.raise_for_status()
        run_id = resp.json()["run_id"]

        elapsed = 0.0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            status_resp = await self._client.get(f"/runs/{run_id}")
            status_resp.raise_for_status()
            run = status_resp.json()

            if run.get("status") == "completed":
                outputs = run.get("outputs", {})
                image_urls = []
                for node_outputs in outputs.values():
                    for item in node_outputs.get("images", []):
                        image_urls.append(item.get("url"))
                return {"run_id": run_id, "image_urls": image_urls,
                        "image_url": image_urls[0] if image_urls else None}

            if run.get("status") in ("failed", "cancelled"):
                raise RuntimeError(f"Comfy Cloud run {run_id} failed: {run.get('error')}")

        raise TimeoutError(f"Comfy Cloud run {run_id} timed out after {max_wait}s")

    async def generate_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit an AnimateDiff workflow."""
        workflow = payload.get("workflow") or _build_animatediff_workflow(payload)
        return await self.generate({"workflow": workflow})

    async def close(self) -> None:
        await self._client.aclose()


def _build_minimal_sdxl_workflow(p: dict) -> dict:
    """Minimal txt2img workflow for SDXL on Comfy Cloud."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": p.get("checkpoint", "sd_xl_base_1.0.safetensors")}},
        "2": {"class_type": "CLIPTextEncode",
              "inputs": {"text": p.get("prompt", ""), "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"text": p.get("negative_prompt", ""), "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": p.get("width", 1024), "height": p.get("height", 1024), "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0], "seed": p.get("seed", 0),
                         "steps": p.get("steps", 20), "cfg": p.get("cfg", 7.0),
                         "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "raingod"}},
    }


def _build_animatediff_workflow(p: dict) -> dict:
    """Stub — replace with a real AnimateDiff workflow JSON."""
    return _build_minimal_sdxl_workflow(p)  # placeholder


# ---------------------------------------------------------------------------
# OpenRouter adapter — 300+ free models
# ---------------------------------------------------------------------------

_OR_BASE = "https://openrouter.ai/api/v1"

_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-r1:free",
]


class OpenRouterAdapter:
    def __init__(self) -> None:
        self._key = os.environ["OPENROUTER_API_KEY"]
        self._client = httpx.AsyncClient(
            base_url=_OR_BASE,
            headers={
                "Authorization": f"Bearer {self._key}",
                "HTTP-Referer": "https://github.com/POWDER-RANGER/raingod-comfy-studio",
                "X-Title": "RainGod Comfy Studio",
            },
            timeout=60.0,
        )

    async def generate(
        self,
        prompt: str,
        model: str = _FREE_MODELS[0],
        system: str | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.post("/chat/completions", json={
            "model": model,
            "messages": messages,
        })
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self._client.aclose()


# ---------------------------------------------------------------------------
# HuggingFace Spaces adapter — AudioCraft MusicGen, Demucs
# ---------------------------------------------------------------------------

_HF_MUSICGEN_SPACE = "https://facebook-musicgen.hf.space"
_HF_DEMUCS_SPACE   = "https://facebook-demucs.hf.space"


class HuggingFaceAdapter:
    def __init__(self) -> None:
        self._token = os.environ.get("HF_TOKEN", "")
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.AsyncClient(headers=headers, timeout=300.0)

    async def musicgen(self, payload: dict) -> dict:
        """Generate music via MusicGen on HuggingFace Spaces (Gradio API)."""
        resp = await self._client.post(
            f"{_HF_MUSICGEN_SPACE}/api/predict",
            json={
                "fn_index": 0,
                "data": [
                    payload.get("prompt", ""),
                    payload.get("duration", 15),
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return {"audio_url": data[0] if data else None, "source": "hf:musicgen"}

    async def demucs(self, payload: dict) -> dict:
        """Stem separation via Demucs on HuggingFace Spaces."""
        audio_url = payload.get("audio_url", "")
        # Download audio, upload to Demucs space
        resp = await self._client.post(
            f"{_HF_DEMUCS_SPACE}/api/predict",
            json={"fn_index": 0, "data": [audio_url]},
        )
        resp.raise_for_status()
        stems = resp.json().get("data", [])
        return {
            "stems": {
                "vocals": stems[0] if len(stems) > 0 else None,
                "drums":  stems[1] if len(stems) > 1 else None,
                "bass":   stems[2] if len(stems) > 2 else None,
                "other":  stems[3] if len(stems) > 3 else None,
            }
        }

    async def close(self) -> None:
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Replicate adapter — overflow image/video
# ---------------------------------------------------------------------------

_REPLICATE_BASE = "https://api.replicate.com/v1"

SDXL_VERSION      = "7762fd07cf82c948538e41f63f77d685e02b063e0thisisplaceholder"
ANIMATEDIFF_VER   = "animatediff-v2v-placeholder"


class ReplicateAdapter:
    def __init__(self) -> None:
        self._key = os.environ["REPLICATE_API_KEY"]
        self._client = httpx.AsyncClient(
            base_url=_REPLICATE_BASE,
            headers={"Authorization": f"Token {self._key}"},
            timeout=300.0,
        )

    async def generate_image(
        self,
        payload: dict,
        poll_interval: float = 2.0,
        max_wait: float = 120.0,
    ) -> dict:
        resp = await self._client.post("/predictions", json={
            "version": SDXL_VERSION,
            "input": {
                "prompt":          payload.get("prompt", ""),
                "negative_prompt": payload.get("negative_prompt", ""),
                "width":           payload.get("width", 1024),
                "height":          payload.get("height", 1024),
                "num_inference_steps": payload.get("steps", 20),
                "guidance_scale":  payload.get("cfg", 7.0),
                "seed":            payload.get("seed", 0),
            },
        })
        resp.raise_for_status()
        prediction = resp.json()
        pred_id = prediction["id"]

        elapsed = 0.0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            get_resp = await self._client.get(f"/predictions/{pred_id}")
            get_resp.raise_for_status()
            pred = get_resp.json()
            if pred.get("status") == "succeeded":
                output = pred.get("output", [])
                image_url = output[0] if output else None
                return {"prediction_id": pred_id, "image_url": image_url}
            if pred.get("status") in ("failed", "canceled"):
                raise RuntimeError(f"Replicate prediction {pred_id} failed")

        raise TimeoutError(f"Replicate prediction {pred_id} timed out")

    async def generate_video(self, payload: dict) -> dict:
        return await self.generate_image(payload)  # placeholder

    async def close(self) -> None:
        await self._client.aclose()
