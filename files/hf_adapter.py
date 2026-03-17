"""HuggingFace Spaces adapter — AudioCraft MusicGen + Demucs stem separation.

Both run on free Spaces GPU. No signup required for public spaces,
but HF_TOKEN gives priority queue access.

Signup: https://huggingface.co/settings/tokens
"""

from __future__ import annotations

import os
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Public Gradio Spaces — these are stable HF-hosted endpoints
# Using the /api/predict Gradio interface
_MUSICGEN_API  = "https://facebook-musicgen.hf.space/api/predict"
_DEMUCS_API    = "https://facebook-demucs.hf.space/api/predict"

# Fallback: Inference API (requires HF_TOKEN for audio models)
_HF_INFERENCE  = "https://api-inference.huggingface.co/models"
_MUSICGEN_MODEL = "facebook/musicgen-small"


class HuggingFaceAdapter:
    """Audio generation and stem separation via HuggingFace Spaces."""

    def __init__(self) -> None:
        self._token = os.environ.get("HF_TOKEN", "")
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.AsyncClient(headers=headers, timeout=300.0)

    async def musicgen(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate music via MusicGen (Gradio Space API).

        Falls back to HF Inference API if Space is unavailable.
        """
        prompt   = payload.get("prompt", "ambient electronic music")
        duration = int(payload.get("duration", 15))

        try:
            resp = await self._client.post(_MUSICGEN_API, json={
                "fn_index": 0,
                "data": [prompt, duration],
            })
            resp.raise_for_status()
            data = resp.json().get("data", [])
            if data and data[0]:
                return {"audio_url": data[0], "source": "hf:musicgen-space"}
        except Exception as e:
            logger.warning("MusicGen Space failed (%s), trying Inference API", e)

        # Fallback: HF Inference API (returns raw audio bytes as base64)
        if self._token:
            resp = await self._client.post(
                f"{_HF_INFERENCE}/{_MUSICGEN_MODEL}",
                json={"inputs": prompt, "parameters": {"duration": duration}},
                headers={"Authorization": f"Bearer {self._token}"},
            )
            if resp.status_code == 200:
                import base64
                b64 = base64.b64encode(resp.content).decode()
                return {"audio_b64": b64, "mime": "audio/wav", "source": "hf:inference-api"}

        raise RuntimeError("MusicGen unavailable — check HF_TOKEN or Space status")

    async def demucs(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Separate audio stems via Demucs (Gradio Space API).

        Returns URLs for vocals, drums, bass, other.
        """
        audio_url = payload.get("audio_url", "")
        if not audio_url:
            raise ValueError("audio_url required for stem separation")

        resp = await self._client.post(_DEMUCS_API, json={
            "fn_index": 0,
            "data": [audio_url],
        })
        resp.raise_for_status()
        stems = resp.json().get("data", [])

        return {
            "stems": {
                "vocals": stems[0] if len(stems) > 0 else None,
                "drums":  stems[1] if len(stems) > 1 else None,
                "bass":   stems[2] if len(stems) > 2 else None,
                "other":  stems[3] if len(stems) > 3 else None,
            },
            "source": "hf:demucs-space",
        }

    async def close(self) -> None:
        await self._client.aclose()
