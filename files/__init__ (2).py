"""Cloud adapter package — lazy imports, only load if env key present."""

from .comfy_cloud_adapter import ComfyCloudAdapter
from .groq_adapter         import GroqAdapter
from .gemini_adapter       import GeminiAdapter
from .suno_adapter         import SunoAdapter
from .openrouter_adapter   import OpenRouterAdapter
from .hf_adapter           import HuggingFaceAdapter
from .replicate_adapter    import ReplicateAdapter

__all__ = [
    "ComfyCloudAdapter",
    "GroqAdapter",
    "GeminiAdapter",
    "SunoAdapter",
    "OpenRouterAdapter",
    "HuggingFaceAdapter",
    "ReplicateAdapter",
]
