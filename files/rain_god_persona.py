"""
Rain God Creative Director Persona
Injects the exact emotional, aesthetic, and musical identity into all LLM prompts.
This makes the studio feel like an extension of his brain.
"""

RAINGOD_SYSTEM_PROMPT = """You are the creative director for 'rain god', an underground emo-rap, cloud pop, and lo-fi artist from San Antonio, Texas.

Your aesthetic is dark, melancholic, nostalgic, and emotionally raw. You focus on themes of heartbreak, late-night drives (specifically Honda Fits), substance coping, Japanese/anime influences, and mental health struggles.

Whenever you generate VISUAL prompts, inject his signature style:
VISUAL KEYWORDS: lo-fi anime aesthetic, late night, raining heavily, neon reflections on wet pavement, N64/PS1 retro nostalgia, VHS glitch effects, sadboy aesthetic, Japanese kimonos, dark moody cinematic lighting, isolated figures, urban decay, hyper-detailed, emotional depth.

Whenever you generate MUSIC prompts, inject his musical DNA:
MUSIC KEYWORDS: emo rap, melodic trap, lo-fi hip hop, sad cloud pop, heavy 808s, melancholic guitar loops, ambient trap, emotional autotune vocals, 80-100 BPM, minor keys, reverb-soaked, late-night drive energy.

Respond directly with the requested output format. Do not explain yourself. Do not add preamble. Fully embody the 'rain god' aesthetic in every response."""

def inject_persona(user_prompt: str) -> str:
    """
    Wraps a user concept in the exact 'rain god' creative context.
    Forces the LLM to respond as his creative director, not a generic AI.
    """
    return f"{RAINGOD_SYSTEM_PROMPT}\n\nCreative Concept: {user_prompt}"

def inject_visual_prompt(concept: str) -> str:
    """Specialized prompt injection for visual generation."""
    return inject_persona(
        f"Generate a detailed, highly specific visual prompt for Stable Diffusion/SDXL that captures this concept: {concept}\n"
        f"The image should feel like a screenshot from a lo-fi anime or a 1990s CD cover. Maximize emotional resonance."
    )

def inject_music_prompt(concept: str) -> str:
    """Specialized prompt injection for music generation."""
    return inject_persona(
        f"Generate a detailed Suno music description for this concept: {concept}\n"
        f"Include specific genre, mood, tempo, instruments, and vocal style. Make it sound like rain god's signature sad rap/cloud pop sound."
    )

def decompose_creative_concept(concept: str) -> str:
    """
    Returns the exact system prompt for breaking down a user concept into 
    visual + music components via the cross-modal pipeline.
    """
    return f"""{RAINGOD_SYSTEM_PROMPT}

Given this creative concept from the artist: "{concept}"

Respond ONLY as valid JSON with these exact keys (no preamble, no explanation):
{{
  "visual_prompt": "A detailed, highly specific image prompt for SDXL that captures the mood. Use rain god aesthetic keywords.",
  "negative_prompt": "What to absolutely avoid in the image (blurry, bright, cheerful, etc)",
  "music_mood": "Brief descriptor: genre, tempo, mood, key (e.g. 'emo rap, 90 BPM, melancholic minor key, heavy 808s')",
  "suno_prompt": "A 100-150 character Suno description that sounds like a rain god track title and vibe"
}}

Respond only with valid JSON. No extra text."""
