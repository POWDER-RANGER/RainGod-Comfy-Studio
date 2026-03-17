"""RainGod Dispatcher — Routes tasks to local Ollama or cloud GPU fleet.

Decision matrix:
  LLM inference      → Ollama local (dolphin-llama3:8b / qwen3:4b / deepseek-r1:1.5b)
  LLM overflow/fast  → Groq (14,400 req/day free) or OpenRouter fallback
  Vision analysis    → moondream:1.8b local → Gemini Flash fallback
  Embeddings         → nomic-embed-text local (always local, fast)
  Image generation   → Comfy Cloud (400 credits/month free, RTX Pro 6000)
  Music generation   → Suno API (50 songs/day free)
  Audio processing   → HuggingFace Spaces (AudioCraft/Demucs, free GPU)
  Overflow rendering → Replicate ($5 free credit)
"""

from __future__ import annotations

import asyncio
import logging
import os
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    LLM_PROMPT     = "llm_prompt"
    LLM_REASONING  = "llm_reasoning"
    LLM_TOOLS      = "llm_tools"
    VISION_ANALYZE = "vision_analyze"
    EMBED          = "embed"
    IMAGE_GENERATE = "image_generate"
    VIDEO_GENERATE = "video_generate"
    MUSIC_GENERATE = "music_generate"
    AUDIO_PROCESS  = "audio_process"
    CROSS_MODAL    = "cross_modal"


class DispatchResult:
    def __init__(self, source: str, data: Any, metadata: dict | None = None):
        self.source = source
        self.data = data
        self.metadata = metadata or {}


class RainGodDispatcher:
    """Central routing layer — instantiate once, inject into FastAPI lifespan.
    All adapters lazy-loaded; only imported if their env key exists.
    """

    def __init__(self) -> None:
        self._ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._adapters_initialized = False
        self._local: Any = None
        self._groq: Any = None
        self._gemini: Any = None
        self._suno: Any = None
        self._comfy_cloud: Any = None
        self._openrouter: Any = None
        self._replicate: Any = None
        self._hf: Any = None

    def _init_adapters(self) -> None:
        if self._adapters_initialized:
            return
        try:
            from .adapters.ollama_adapter import OllamaAdapter
            self._local = OllamaAdapter(base_url=self._ollama_url)
            logger.info("Ollama adapter ready at %s", self._ollama_url)
        except Exception as e:
            logger.warning("Ollama adapter failed: %s", e)

        if os.getenv("GROQ_API_KEY"):
            from .adapters.groq_adapter import GroqAdapter
            self._groq = GroqAdapter()
            logger.info("Groq adapter ready")

        if os.getenv("GEMINI_API_KEY"):
            from .adapters.gemini_adapter import GeminiAdapter
            self._gemini = GeminiAdapter()
            logger.info("Gemini adapter ready")

        if os.getenv("SUNO_API_KEY"):
            from .adapters.suno_adapter import SunoAdapter
            self._suno = SunoAdapter()
            logger.info("Suno adapter ready")

        if os.getenv("COMFY_API_KEY"):
            from .adapters.comfy_cloud_adapter import ComfyCloudAdapter
            self._comfy_cloud = ComfyCloudAdapter()
            logger.info("ComfyCloud adapter ready")

        if os.getenv("OPENROUTER_API_KEY"):
            from .adapters.openrouter_adapter import OpenRouterAdapter
            self._openrouter = OpenRouterAdapter()
            logger.info("OpenRouter adapter ready")

        if os.getenv("REPLICATE_API_KEY"):
            from .adapters.replicate_adapter import ReplicateAdapter
            self._replicate = ReplicateAdapter()
            logger.info("Replicate adapter ready")

        if os.getenv("HF_TOKEN"):
            from .adapters.hf_adapter import HuggingFaceAdapter
            self._hf = HuggingFaceAdapter()
            logger.info("HuggingFace adapter ready")

        self._adapters_initialized = True

    async def dispatch(
        self,
        task_type: TaskType,
        payload: dict[str, Any],
        prefer_local: bool = True,
    ) -> DispatchResult:
        """Route a task to the optimal adapter."""
        self._init_adapters()
        dispatch_map = {
            TaskType.LLM_PROMPT:     self._dispatch_llm,
            TaskType.LLM_REASONING:  self._dispatch_reasoning,
            TaskType.LLM_TOOLS:      self._dispatch_tools,
            TaskType.VISION_ANALYZE: self._dispatch_vision,
            TaskType.EMBED:          self._dispatch_embed,
            TaskType.IMAGE_GENERATE: self._dispatch_image,
            TaskType.VIDEO_GENERATE: self._dispatch_video,
            TaskType.MUSIC_GENERATE: self._dispatch_music,
            TaskType.AUDIO_PROCESS:  self._dispatch_audio,
            TaskType.CROSS_MODAL:    self._dispatch_cross_modal,
        }
        handler = dispatch_map.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")
        result = await handler(payload, prefer_local=prefer_local)
        logger.info("Dispatched %s → %s", task_type.value, result.source)
        return result

    async def _dispatch_llm(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        prompt = payload.get("prompt", "")
        model  = payload.get("model", "dolphin-llama3:8b")
        if prefer_local and self._local:
            text = await self._local.generate(prompt=prompt, model=model)
            return DispatchResult(source="ollama", data={"text": text})
        if self._groq:
            text = await self._groq.generate(prompt=prompt)
            return DispatchResult(source="groq", data={"text": text})
        if self._openrouter:
            text = await self._openrouter.generate(prompt=prompt)
            return DispatchResult(source="openrouter", data={"text": text})
        raise RuntimeError("No LLM adapter available")

    async def _dispatch_reasoning(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        prompt = payload.get("prompt", "")
        if prefer_local and self._local:
            text = await self._local.generate(prompt=prompt, model="deepseek-r1:1.5b")
            return DispatchResult(source="ollama:deepseek-r1", data={"text": text})
        if self._groq:
            text = await self._groq.generate(prompt=prompt, model="deepseek-r1-distill-llama-70b")
            return DispatchResult(source="groq:deepseek-r1-70b", data={"text": text})
        raise RuntimeError("No reasoning adapter available")

    async def _dispatch_tools(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        prompt = payload.get("prompt", "")
        schema = payload.get("schema")
        if prefer_local and self._local:
            text = await self._local.generate(prompt=prompt, model="qwen3:4b", format="json" if schema else None)
            return DispatchResult(source="ollama:qwen3", data={"text": text})
        if self._groq:
            text = await self._groq.generate(prompt=prompt, model="llama3-groq-70b-8192-tool-use-preview")
            return DispatchResult(source="groq:llama3-tool-use", data={"text": text})
        raise RuntimeError("No tools adapter available")

    async def _dispatch_vision(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        image_b64 = payload.get("image_b64")
        image_url = payload.get("image_url")
        question  = payload.get("question", "Describe this image in detail.")
        if prefer_local and self._local and image_url:
            text = await self._local.vision(model="moondream:1.8b", image_url=image_url, prompt=question)
            return DispatchResult(source="ollama:moondream", data={"text": text})
        if self._gemini:
            text = await self._gemini.vision(image_b64=image_b64, image_url=image_url, prompt=question)
            return DispatchResult(source="gemini-flash", data={"text": text})
        raise RuntimeError("No vision adapter available")

    async def _dispatch_embed(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        text = payload.get("text", "")
        if self._local:
            embedding = await self._local.embed(model="nomic-embed-text", text=text)
            return DispatchResult(source="ollama:nomic-embed", data={"embedding": embedding})
        raise RuntimeError("Ollama adapter required for embeddings")

    async def _dispatch_image(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        if self._comfy_cloud:
            result = await self._comfy_cloud.generate(payload)
            return DispatchResult(source="comfy-cloud", data=result)
        if self._replicate:
            result = await self._replicate.generate_image(payload)
            return DispatchResult(source="replicate", data=result)
        from .comfyui_client import ComfyUIClient
        from .workflow_builder import WorkflowBuilder
        local_client = ComfyUIClient()
        wf = WorkflowBuilder().build_txt2img(
            positive=payload.get("prompt", ""),
            negative=payload.get("negative_prompt", ""),
            width=payload.get("width", 1024),
            height=payload.get("height", 1024),
            steps=payload.get("steps", 20),
            cfg=payload.get("cfg", 7.0),
            sampler_name="euler",
            scheduler="normal",
            seed=payload.get("seed", 0),
        )
        prompt_id = local_client.queue_prompt(wf)
        return DispatchResult(source="comfyui-local", data={"prompt_id": prompt_id})

    async def _dispatch_video(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        if self._comfy_cloud:
            result = await self._comfy_cloud.generate_video(payload)
            return DispatchResult(source="comfy-cloud:animatediff", data=result)
        if self._replicate:
            result = await self._replicate.generate_video(payload)
            return DispatchResult(source="replicate:animatediff", data=result)
        raise RuntimeError("No video generation adapter available")

    async def _dispatch_music(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        if self._suno:
            result = await self._suno.generate(payload)
            return DispatchResult(source="suno", data=result)
        if self._hf:
            result = await self._hf.musicgen(payload)
            return DispatchResult(source="hf:musicgen", data=result)
        raise RuntimeError("No music adapter available")

    async def _dispatch_audio(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        if self._hf:
            result = await self._hf.demucs(payload)
            return DispatchResult(source="hf:demucs", data=result)
        raise RuntimeError("HuggingFace adapter required for audio processing")

    async def _dispatch_cross_modal(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        user_prompt = payload.get("prompt", "")
        decompose_prompt = (
            f"Given this creative concept: '{user_prompt}'\n"
            "Respond in JSON with exactly these keys:\n"
            "  visual_prompt: (detailed image generation prompt)\n"
            "  negative_prompt: (what to avoid visually)\n"
            "  music_mood: (music genre, tempo, key, vibe descriptor)\n"
            "  suno_prompt: (Suno song description, max 200 chars)\n"
            "No preamble, pure JSON only."
        )
        decomp = await self._dispatch_tools({"prompt": decompose_prompt, "schema": True})
        import json
        try:
            parts = json.loads(decomp.data["text"])
        except Exception:
            parts = {
                "visual_prompt": user_prompt,
                "negative_prompt": "blurry, low quality",
                "music_mood": "ambient, reflective",
                "suno_prompt": f"ambient music for: {user_prompt[:100]}",
            }
        img_result = await self._dispatch_image({
            "prompt": parts.get("visual_prompt", user_prompt),
            "negative_prompt": parts.get("negative_prompt", ""),
            "width": payload.get("width", 1024),
            "height": payload.get("height", 1024),
        })
        vision_analysis = None
        img_url = img_result.data.get("image_url")
        if img_url:
            vis = await self._dispatch_vision({
                "image_url": img_url,
                "question": (
                    "Analyze the mood, color palette, and atmosphere of this image. "
                    "Give a 2-sentence music direction based on what you see."
                ),
            })
            vision_analysis = vis.data.get("text", "")
            parts["suno_prompt"] = f"{parts['suno_prompt']}. Visual mood: {vision_analysis[:100]}"
        music_result = await self._dispatch_music({
            "prompt": parts.get("suno_prompt", user_prompt),
            "duration": payload.get("duration", 30),
            "tags": parts.get("music_mood", "ambient"),
        })
        return DispatchResult(
            source="cross-modal-pipeline",
            data={
                "image": img_result.data,
                "music": music_result.data,
                "vision_analysis": vision_analysis,
                "decomposition": parts,
                "pipeline_sources": {
                    "llm": decomp.source,
                    "image": img_result.source,
                    "music": music_result.source,
                },
            },
        )

    def status(self) -> dict[str, Any]:
        self._init_adapters()
        return {
            "local_ollama": self._local is not None,
            "groq":         self._groq is not None,
            "gemini":       self._gemini is not None,
            "suno":         self._suno is not None,
            "comfy_cloud":  self._comfy_cloud is not None,
            "openrouter":   self._openrouter is not None,
            "replicate":    self._replicate is not None,
            "huggingface":  self._hf is not None,
        }
