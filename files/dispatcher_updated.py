"""
DISPATCHER.PY — UPDATED WITH RAIN GOD PERSONA INJECTION
Central routing layer that now speaks in rain god's voice.
"""

from __future__ import annotations
import asyncio
import logging
import os
from enum import Enum
from typing import Any
from rain_god_persona import decompose_creative_concept, inject_persona

logger = logging.getLogger(__name__)

class TaskType(str, Enum):
    LLMPROMPT = "llmprompt"
    LLMREASONING = "llmreasoning"
    LLMTOOLS = "llmtools"
    VISIONANALYZE = "visionanalyze"
    EMBED = "embed"
    IMAGEGENERATE = "imagegenerate"
    VIDEOGENERATE = "videogenerate"
    MUSICGENERATE = "musicgenerate"
    AUDIOPROCESS = "audioprocess"
    CROSSMODAL = "crossmodal"

class DispatchResult:
    def __init__(self, source: str, data: Any, metadata: dict = None):
        self.source = source  # Which adapter handled it
        self.data = data
        self.metadata = metadata or {}

class RainGodDispatcher:
    """
    Central routing layer for the Rain God Comfy Studio.
    Lazy-loads all adapters. Routes tasks to local Ollama or cloud GPU fleet.
    NOW INJECTS THE RAIN GOD PERSONA INTO ALL LLM CALLS.
    """
    
    def __init__(self) -> None:
        self.ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.adapters_initialized = False
        
        # Local
        self.local = None
        
        # Cloud
        self.groq = None
        self.gemini = None
        self.suno = None
        self.comfy_cloud = None
        self.openrouter = None
        self.replicate = None
        self.hf = None

    def init_adapters(self) -> None:
        if self.adapters_initialized:
            return
        
        try:
            from local_adapters.ollama_adapter import OllamaAdapter
            self.local = OllamaAdapter(base_url=self.ollama_url)
            logger.info(f"Ollama adapter ready at {self.ollama_url}")
        except Exception as e:
            logger.warning(f"Ollama adapter failed: {e}")

        if os.getenv("GROQ_API_KEY"):
            from cloud_adapters.groq_adapter import GroqAdapter
            self.groq = GroqAdapter()
            logger.info("Groq adapter ready")

        if os.getenv("GEMINI_API_KEY"):
            from cloud_adapters.gemini_adapter import GeminiAdapter
            self.gemini = GeminiAdapter()
            logger.info("Gemini adapter ready")

        if os.getenv("SUNO_API_KEY"):
            from cloud_adapters.suno_adapter import SunoAdapter
            self.suno = SunoAdapter()
            logger.info("Suno adapter ready")

        if os.getenv("COMFY_API_KEY"):
            from cloud_adapters.comfy_cloud_adapter import ComfyCloudAdapter
            self.comfy_cloud = ComfyCloudAdapter()
            logger.info("ComfyCloud adapter ready")

        if os.getenv("OPENROUTER_API_KEY"):
            from cloud_adapters.openrouter_adapter import OpenRouterAdapter
            self.openrouter = OpenRouterAdapter()
            logger.info("OpenRouter adapter ready")

        if os.getenv("REPLICATE_API_KEY"):
            from cloud_adapters.replicate_adapter import ReplicateAdapter
            self.replicate = ReplicateAdapter()
            logger.info("Replicate adapter ready")

        if os.getenv("HF_TOKEN"):
            from cloud_adapters.hf_adapter import HuggingFaceAdapter
            self.hf = HuggingFaceAdapter()
            logger.info("HuggingFace adapter ready")

        self.adapters_initialized = True

    async def dispatch(
        self, 
        task_type: TaskType, 
        payload: dict[str, Any], 
        prefer_local: bool = True
    ) -> DispatchResult:
        """Route a task to the optimal adapter."""
        self.init_adapters()
        
        dispatch_map = {
            TaskType.LLMPROMPT: self.dispatch_llm,
            TaskType.LLMREASONING: self.dispatch_reasoning,
            TaskType.LLMTOOLS: self.dispatch_tools,
            TaskType.VISIONANALYZE: self.dispatch_vision,
            TaskType.EMBED: self.dispatch_embed,
            TaskType.IMAGEGENERATE: self.dispatch_image,
            TaskType.VIDEOGENERATE: self.dispatch_video,
            TaskType.MUSICGENERATE: self.dispatch_music,
            TaskType.AUDIOPROCESS: self.dispatch_audio,
            TaskType.CROSSMODAL: self.dispatch_crossmodal,
        }
        
        handler = dispatch_map.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type.value}")
        
        result = await handler(payload, prefer_local)
        logger.info(f"Dispatched {task_type.value} → {result.source}")
        return result

    # ======================== LLM TASKS ========================
    
    async def dispatch_llm(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        """General LLM inference with Rain God persona injection."""
        prompt = payload.get("prompt", "")
        model = payload.get("model", "dolphin-llama3:8b")
        
        # INJECT THE RAIN GOD PERSONA
        prompt = inject_persona(prompt)
        
        if prefer_local and self.local:
            text = await self.local.generate(prompt, model)
            return DispatchResult(source="ollama", data=text)
        
        if self.groq:
            text = await self.groq.generate(prompt)
            return DispatchResult(source="groq", data=text)
        
        if self.openrouter:
            text = await self.openrouter.generate(prompt)
            return DispatchResult(source="openrouter", data=text)
        
        raise RuntimeError("No LLM adapter available")

    async def dispatch_reasoning(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        """Deep reasoning with persona."""
        prompt = payload.get("prompt", "")
        
        # INJECT THE RAIN GOD PERSONA
        prompt = inject_persona(prompt)
        
        if prefer_local and self.local:
            text = await self.local.generate(prompt, model="deepseek-r1:1.5b")
            return DispatchResult(source="ollama:deepseek-r1", data=text)
        
        if self.groq:
            text = await self.groq.generate(prompt, model="deepseek-r1-distill-llama-70b")
            return DispatchResult(source="groq:deepseek-r1-70b", data=text)
        
        raise RuntimeError("No reasoning adapter available")

    async def dispatch_tools(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        """Tool-use with structured JSON output."""
        prompt = payload.get("prompt", "")
        schema = payload.get("schema")
        
        # INJECT THE RAIN GOD PERSONA
        prompt = inject_persona(prompt)
        
        if prefer_local and self.local:
            text = await self.local.generate(
                prompt, 
                model="qwen3:4b", 
                format="json" if schema else None
            )
            return DispatchResult(source="ollama:qwen3", data=text)
        
        if self.groq:
            text = await self.groq.generate(
                prompt, 
                model="llama3-groq-70b-8192-tool-use-preview"
            )
            return DispatchResult(source="groq:llama3-tool-use", data=text)
        
        raise RuntimeError("No tools adapter available")

    # ======================== VISION TASK ========================
    
    async def dispatch_vision(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        """Vision analysis with persona."""
        image_b64 = payload.get("image_b64")
        image_url = payload.get("image_url")
        question = payload.get("question", "Describe this image in detail.")
        
        if prefer_local and self.local and image_url:
            text = await self.local.vision(
                model="moondream:1.8b",
                image_url=image_url,
                prompt=question
            )
            return DispatchResult(source="ollama:moondream", data=text)
        
        if self.gemini:
            text = await self.gemini.vision(
                image_b64=image_b64,
                image_url=image_url,
                prompt=question
            )
            return DispatchResult(source="gemini-flash", data=text)
        
        raise RuntimeError("No vision adapter available")

    # ======================== EMBEDDING TASK ========================
    
    async def dispatch_embed(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        """Embeddings are always local (nomic-embed-text)."""
        text = payload.get("text", "")
        
        if self.local:
            embedding = await self.local.embed(model="nomic-embed-text", text=text)
            return DispatchResult(source="ollama:nomic-embed", data=embedding)
        
        raise RuntimeError("Ollama adapter required for embeddings")

    # ======================== IMAGE GENERATION ========================
    
    async def dispatch_image(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        """Image generation via Comfy Cloud (primary) or Replicate (fallback)."""
        from raingod_workflows import get_preset, merge_preset_with_payload
        
        # Get the Rain God SDXL preset and merge with user overrides
        preset_name = payload.get("preset", "sdxl_lofi")
        merged_payload = merge_preset_with_payload(preset_name, payload)
        
        if self.comfy_cloud:
            result = await self.comfy_cloud.generate(merged_payload)
            return DispatchResult(source="comfy-cloud", data=result)
        
        if self.replicate:
            result = await self.replicate.generate_image(merged_payload)
            return DispatchResult(source="replicate", data=result)
        
        raise RuntimeError("No image generation adapter available")

    # ======================== VIDEO GENERATION ========================
    
    async def dispatch_video(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        """Video generation via Comfy Cloud or Replicate."""
        if self.comfy_cloud:
            result = await self.comfy_cloud.generate_video(payload)
            return DispatchResult(source="comfy-cloud:animatediff", data=result)
        
        if self.replicate:
            result = await self.replicate.generate_video(payload)
            return DispatchResult(source="replicate:animatediff", data=result)
        
        raise RuntimeError("No video generation adapter available")

    # ======================== MUSIC GENERATION ========================
    
    async def dispatch_music(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        """Music generation via Suno (primary) or HuggingFace AudioCraft (fallback)."""
        if self.suno:
            result = await self.suno.generate(payload)
            return DispatchResult(source="suno", data=result)
        
        if self.hf:
            result = await self.hf.musicgen(payload)
            return DispatchResult(source="hf:musicgen", data=result)
        
        raise RuntimeError("No music adapter available")

    # ======================== AUDIO PROCESSING ========================
    
    async def dispatch_audio(self, payload: dict, prefer_local: bool = False) -> DispatchResult:
        """Audio processing (stem separation) via HuggingFace Demucs."""
        if self.hf:
            result = await self.hf.demucs(payload)
            return DispatchResult(source="hf:demucs", data=result)
        
        raise RuntimeError("HuggingFace adapter required for audio processing")

    # ======================== CROSS-MODAL PIPELINE ========================
    # THIS IS THE CROWN JEWEL — FULLY PERSONA-INJECTED
    
    async def dispatch_crossmodal(self, payload: dict, prefer_local: bool = True) -> DispatchResult:
        """
        Full cross-modal pipeline with Rain God persona injection at every step.
        
        Steps:
        1. User concept → LLM decomposition (visual + music mood)
        2. Comfy Cloud renders visual
        3. moondream analyzes visual for mood/palette
        4. Suno generates music enriched with visual feedback
        """
        user_prompt = payload.get("prompt", "")
        
        # ===== STEP 1: LLM Decomposition with Rain God Persona =====
        decompose_prompt = decompose_creative_concept(user_prompt)
        decomp = await self.dispatch_tools(
            {"prompt": decompose_prompt, "schema": True},
            prefer_local=prefer_local
        )
        
        import json
        try:
            parts = json.loads(decomp.data)
        except:
            parts = {
                "visual_prompt": user_prompt,
                "negative_prompt": "blurry, low quality",
                "music_mood": "ambient, melancholic, sad rap",
                "suno_prompt": f"sad lo-fi track inspired by: {user_prompt[:100]}"
            }
        
        # ===== STEP 2: Generate Image =====
        img_result = await self.dispatch_image({
            "prompt": parts.get("visual_prompt", user_prompt),
            "negative_prompt": parts.get("negative_prompt", ""),
            "width": payload.get("width", 1024),
            "height": payload.get("height", 1024),
            "preset": "sdxl_lofi"
        })
        
        # ===== STEP 3: Vision Analysis of Generated Image =====
        vision_analysis = None
        img_url = img_result.data.get("image_url") if isinstance(img_result.data, dict) else None
        if img_url:
            vis = await self.dispatch_vision({
                "image_url": img_url,
                "question": "Analyze the mood, color palette, and atmosphere of this image. Give a 2-sentence music direction based on what you see."
            })
            vision_analysis = vis.data
        
        # ===== STEP 4: Enrich Music Prompt with Vision Feedback =====
        enriched_suno = f"{parts.get('suno_prompt', '')}. Visual mood: {vision_analysis[:100] if vision_analysis else 'moody rain aesthetic'}"
        
        # ===== STEP 5: Generate Music =====
        music_result = await self.dispatch_music({
            "prompt": enriched_suno,
            "duration": payload.get("duration", 30),
            "tags": parts.get("music_mood", "ambient, sad rap")
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
                    "music": music_result.source
                }
            }
        )

    # ======================== STATUS CHECK ========================
    
    def status(self) -> dict[str, Any]:
        self.init_adapters()
        return {
            "local_ollama": self.local is not None,
            "groq": self.groq is not None,
            "gemini": self.gemini is not None,
            "suno": self.suno is not None,
            "comfy_cloud": self.comfy_cloud is not None,
            "openrouter": self.openrouter is not None,
            "replicate": self.replicate is not None,
            "huggingface": self.hf is not None,
        }
