"""RAINGOD Backend Configuration.

Central configuration module for all RAINGOD ComfyUI Integration settings.
All presets, hardware detection, quality tiers, and operational parameters
are defined here so the rest of the backend remains configuration-agnostic.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class QualityTier(str, Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    FINAL = "final"


class GPUTier(str, Enum):
    CPU_ONLY = "cpu"
    LOW_VRAM = "low_vram"    # < 8 GB
    MID_VRAM = "mid_vram"    # 8–16 GB
    HIGH_VRAM = "high_vram"  # > 16 GB


# ---------------------------------------------------------------------------
# Resolution Presets
# ---------------------------------------------------------------------------

RESOLUTION_PRESETS: dict[str, dict[str, int]] = {
    "thumbnail":      {"width": 512,  "height": 512},
    "cover_art":      {"width": 1024, "height": 1024},
    "banner":         {"width": 1920, "height": 1080},
    "video_frame":    {"width": 1920, "height": 1080},
    "high_res":       {"width": 2048, "height": 2048},
    "4k":             {"width": 3840, "height": 2160},
    "vertical_video": {"width": 1080, "height": 1920},
}


# ---------------------------------------------------------------------------
# Sampler Presets
# ---------------------------------------------------------------------------

@dataclass
class SamplerPreset:
    steps: int
    cfg: float
    sampler_name: str
    scheduler: str
    denoise: float = 1.0
    description: str = ""


SAMPLER_PRESETS: dict[str, SamplerPreset] = {
    "fast": SamplerPreset(
        steps=20,
        cfg=7.0,
        sampler_name="euler",
        scheduler="normal",
        description="Fast generation — good for drafts and previews",
    ),
    "quality": SamplerPreset(
        steps=40,
        cfg=7.5,
        sampler_name="dpmpp_2m",
        scheduler="karras",
        description="Balanced quality/speed for most production use",
    ),
    "ultra": SamplerPreset(
        steps=80,
        cfg=8.5,
        sampler_name="dpmpp_sde",
        scheduler="karras",
        description="Maximum quality — slow; use for final masters",
    ),
    "gpu_low": SamplerPreset(
        steps=20,
        cfg=7.0,
        sampler_name="euler_a",
        scheduler="normal",
        description="Optimised for GPUs with < 8 GB VRAM",
    ),
    "gpu_high": SamplerPreset(
        steps=60,
        cfg=8.0,
        sampler_name="dpmpp_2m_sde",
        scheduler="exponential",
        description="Optimised for GPUs with > 16 GB VRAM",
    ),
}


# ---------------------------------------------------------------------------
# LoRA Mappings
# ---------------------------------------------------------------------------

@dataclass
class LoRAConfig:
    filename: str
    strength_model: float = 0.8
    strength_clip: float = 0.8
    description: str = ""


LORA_MAPPINGS: dict[str, LoRAConfig] = {
    "raingod_style":  LoRAConfig("raingod_v1.safetensors",  description="RAINGOD house aesthetic"),
    "album_cover":    LoRAConfig("album_aesthetic_v2.safetensors", description="Professional album cover composition"),
    "video_aesthetic":LoRAConfig("cinematic_v3.safetensors", description="Cinematic colour grading"),
    "synthwave":      LoRAConfig("synthwave_v2.safetensors", description="1980s synthwave / retrowave style"),
    "cyberpunk":      LoRAConfig("cyberpunk_v1.safetensors", description="Neon cyberpunk cityscape"),
    "abstract":       LoRAConfig("abstract_art_v1.safetensors", description="Geometric abstract art"),
    "dark_moody":     LoRAConfig("dark_aesthetic_v1.safetensors", description="Dark atmospheric mood"),
}


# ---------------------------------------------------------------------------
# Quality Tier Configuration
# ---------------------------------------------------------------------------

QUALITY_TIERS: dict[QualityTier, dict[str, Any]] = {
    QualityTier.DRAFT: {
        "sampler_preset": "fast",
        "resolution": "thumbnail",
        "upscale": False,
        "lora_strength": 0.6,
    },
    QualityTier.STANDARD: {
        "sampler_preset": "quality",
        "resolution": "cover_art",
        "upscale": False,
        "lora_strength": 0.8,
    },
    QualityTier.FINAL: {
        "sampler_preset": "ultra",
        "resolution": "high_res",
        "upscale": True,
        "lora_strength": 0.9,
    },
}


# ---------------------------------------------------------------------------
# GPU Hardware Detection
# ---------------------------------------------------------------------------

def detect_gpu_tier() -> GPUTier:
    """Detect GPU capability and return appropriate tier.

    Tries ``nvidia-smi`` first; falls back to CPU-only if unavailable.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            vram_mb = int(result.stdout.strip().splitlines()[0])
            vram_gb = vram_mb / 1024
            logger.info("GPU detected: %.1f GB VRAM", vram_gb)
            if vram_gb < 8:
                return GPUTier.LOW_VRAM
            if vram_gb <= 16:
                return GPUTier.MID_VRAM
            return GPUTier.HIGH_VRAM
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass

    logger.warning("No NVIDIA GPU detected — falling back to CPU mode")
    return GPUTier.CPU_ONLY


# ---------------------------------------------------------------------------
# Batch Processing Configuration
# ---------------------------------------------------------------------------

@dataclass
class BatchConfig:
    max_concurrent: int = 4
    max_queue_size: int = 100
    timeout_per_image: int = 300  # seconds
    retry_attempts: int = 3
    retry_delay_base: float = 2.0  # exponential backoff base


# ---------------------------------------------------------------------------
# Audio-Visual Sync Configuration
# ---------------------------------------------------------------------------

@dataclass
class AudioVisualSyncConfig:
    fps: int = 30
    beat_detection_enabled: bool = True
    scene_change_threshold: float = 0.3
    min_scene_duration: float = 1.5  # seconds
    max_scene_duration: float = 10.0  # seconds
    transition_frames: int = 15


# ---------------------------------------------------------------------------
# Cache Configuration
# ---------------------------------------------------------------------------

@dataclass
class CacheConfig:
    enabled: bool = True
    max_size_mb: int = 2048
    ttl_seconds: int = 3600
    dedup_enabled: bool = True  # hash-based deduplication


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "json"  # "json" | "text"
    include_request_id: bool = True
    log_to_file: bool = True
    log_dir: str = "logs"
    max_file_size_mb: int = 100
    backup_count: int = 5


# ---------------------------------------------------------------------------
# ComfyUI API Configuration
# ---------------------------------------------------------------------------

@dataclass
class ComfyUIConfig:
    host: str = field(default_factory=lambda: os.getenv("COMFYUI_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("COMFYUI_PORT", "8188")))
    timeout: int = 300
    health_check_interval: int = 30

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def prompt_url(self) -> str:
        return f"{self.base_url}/prompt"

    @property
    def history_url(self) -> str:
        return f"{self.base_url}/history"

    @property
    def queue_url(self) -> str:
        return f"{self.base_url}/queue"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws"


# ---------------------------------------------------------------------------
# Root Config Object
# ---------------------------------------------------------------------------

@dataclass
class RainGodConfig:
    """Top-level configuration object.

    Instantiate once and pass through the application.
    """

    comfyui: ComfyUIConfig = field(default_factory=ComfyUIConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    audio_visual: AudioVisualSyncConfig = field(default_factory=AudioVisualSyncConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    gpu_tier: GPUTier = field(default_factory=detect_gpu_tier)

    # Convenient passthrough accessors for global presets
    resolution_presets: dict[str, dict[str, int]] = field(
        default_factory=lambda: RESOLUTION_PRESETS
    )
    sampler_presets: dict[str, SamplerPreset] = field(
        default_factory=lambda: SAMPLER_PRESETS
    )
    lora_mappings: dict[str, LoRAConfig] = field(
        default_factory=lambda: LORA_MAPPINGS
    )
    quality_tiers: dict[QualityTier, dict[str, Any]] = field(
        default_factory=lambda: QUALITY_TIERS
    )


# Module-level singleton — import this everywhere
config = RainGodConfig()
