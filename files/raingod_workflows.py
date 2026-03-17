"""
RainGod ComfyUI Workflow Presets
Pre-built SDXL/Flux workflows tuned for his lo-fi anime, nostalgic aesthetic.
Load these directly from the UI or via the dispatcher.
"""

import json

RAINGOD_SDXL_PRESET = {
    "name": "Rain God - SDXL Lo-Fi Anime",
    "description": "SDXL optimized for rain god's aesthetic: lo-fi anime, late-night, moody, retro nostalgia",
    "model": "SDXL",
    "params": {
        "checkpoint": "sdxl_1.0.safetensors",
        "positive_prompt": "(lo-fi anime aesthetic:1.3), late night, raining heavily, neon reflections, sadboy aesthetic, VHS glitch, minor key energy, hyper-detailed",
        "negative_prompt": "bright, cheerful, saturated colors, daylight, clear sky, digital art, 3d render, cartoon, unrealistic, blurry, low quality",
        "width": 1024,
        "height": 1024,
        "steps": 25,
        "cfg_scale": 7.0,
        "sampler": "euler",
        "scheduler": "normal",
        "seed": 0,
        "denoise": 1.0
    }
}

RAINGOD_FLUX_PRESET = {
    "name": "Rain God - Flux Ultra",
    "description": "Flux optimized for maximum emotional depth and photorealism within his aesthetic",
    "model": "Flux",
    "params": {
        "checkpoint": "flux_dev.safetensors",
        "positive_prompt": "(lo-fi anime aesthetic:1.2), late night photography, raining, neon city lights reflecting off wet streets, emotional, cinematic, 1990s vibe, Japanese aesthetic, moody color grading",
        "negative_prompt": "bright, cheerful, cartoon, digital art, unrealistic, blurry",
        "width": 1024,
        "height": 1024,
        "steps": 20,
        "cfg_scale": 7.5,
        "sampler": "euler",
        "scheduler": "normal",
        "seed": 0,
        "denoise": 1.0
    }
}

RAINGOD_ANIMATEDIFF_PRESET = {
    "name": "Rain God - VHS Dream Animation",
    "description": "AnimateDiff for video: rain, car interiors, late-night motion, melancholic energy",
    "model": "AnimateDiff",
    "params": {
        "motion_model": "mm_sd15_v3.ckpt",
        "positive_prompt": "(lo-fi anime aesthetic:1.2), late night drive, raining, Honda Fit interior, dashboard lights, wet windshield, melancholic motion, VHS glitch effect, cinematic, emotional",
        "negative_prompt": "bright, daytime, cheerful, cartoon",
        "width": 512,
        "height": 512,
        "steps": 20,
        "cfg_scale": 7.0,
        "frames": 16,
        "fps": 8,
        "motion_strength": 1.0
    }
}

PRESETS = {
    "sdxl_lofi": RAINGOD_SDXL_PRESET,
    "flux_ultra": RAINGOD_FLUX_PRESET,
    "animatediff_vhs": RAINGOD_ANIMATEDIFF_PRESET
}

def get_preset(preset_name: str) -> dict:
    """Fetch a pre-built workflow preset by name."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    return PRESETS[preset_name]

def list_presets() -> list:
    """Return all available preset names and descriptions."""
    return [
        {"name": k, "desc": v["description"]} 
        for k, v in PRESETS.items()
    ]

def merge_preset_with_payload(preset_name: str, user_payload: dict) -> dict:
    """
    Merge a preset with user overrides.
    User values take precedence over preset defaults.
    """
    preset = get_preset(preset_name)
    merged = preset["params"].copy()
    merged.update(user_payload)
    return merged
