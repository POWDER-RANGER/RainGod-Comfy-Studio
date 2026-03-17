# RainGod Comfy Studio — Architecture

## Repository Layout

```
raingod-comfy-studio/
├── switchboard/
│   └── index.html            ← Full node-graph UI (self-contained)
├── backend/
│   ├── dispatcher.py          ← CORE: routes tasks to local/cloud
│   ├── dispatch_routes.py     ← FastAPI /dispatch endpoints
│   ├── rain_backend.py        ← Main FastAPI app (from RAINGOD-ComfyUI-Integration)
│   ├── rain_backend_config.py ← All presets and config
│   ├── comfyui_client.py      ← Local ComfyUI client (circuit breaker, retry)
│   ├── workflow_builder.py    ← ComfyUI graph assembler
│   ├── lora_manager.py        ← LoRA registry + chain builder
│   ├── local_adapters/
│   │   └── ollama_adapter.py  ← Ollama: generate, chat, vision, embed
│   └── cloud_adapters/
│       ├── __init__.py        ← ComfyCloud, OpenRouter, HuggingFace, Replicate
│       ├── groq_adapter.py    ← Groq LPU
│       ├── gemini_adapter.py  ← Google Gemini Flash
│       └── suno_adapter.py    ← Suno music generation
├── scripts/
│   ├── deploy_api_keys.ps1   ← Interactive key deployment (Windows)
│   └── validate_keys.py      ← Async health check for all 8 services
├── workflows/                 ← ComfyUI JSON templates (from integration repo)
├── tests/                     ← Test suite (from integration repo)
├── .env.example               ← All 8 API keys documented
└── STUDIO_ARCHITECTURE.md    ← This file
```

## Dispatch Decision Matrix

| Task | Primary | Fallback | Notes |
|------|---------|----------|-------|
| LLM general | dolphin-llama3:8b local | Groq llama3-70b | 4.7GB, uncensored |
| LLM reasoning | deepseek-r1:1.5b local | Groq deepseek-r1-70b | chain-of-thought |
| LLM tools/JSON | qwen3:4b local | Groq llama3-tool-use | structured output |
| Vision | moondream:1.8b local | Gemini Flash | image URL or b64 |
| Embeddings | nomic-embed-text local | — | always local |
| Image gen | Comfy Cloud (RTX Pro 6000) | Replicate → local ComfyUI | 400 credits/mo |
| Video gen | Comfy Cloud AnimateDiff | Replicate | cloud GPU only |
| Music gen | Suno (50 songs/day) | HF AudioCraft | full vocals |
| Stem separation | HF Demucs Spaces | — | free GPU |
| Cross-modal | Full pipeline | — | see below |

## Cross-Modal Pipeline

```
User prompt: "Dark cyberpunk rain scene, melancholic"
      │
      ▼  qwen3:4b (local) — tool-use JSON decomposition
      │   → visual_prompt, negative_prompt, suno_prompt, music_mood
      │
      ▼  Comfy Cloud — SDXL image generation
      │   → image_url
      │
      ▼  moondream:1.8b (local) — vision analysis
      │   → "dark blues, high contrast, isolated figure, rain"
      │   (enriches suno_prompt with visual feedback)
      │
      ▼  Suno API — music generation
          → audio_url, clip_id
```

## Node Types in UI

| Node | Task | Local/Cloud | Output |
|------|------|------------|--------|
| LLM Prompt | llm_prompt | dolphin→Groq | text |
| Reasoning | llm_reasoning | deepseek-r1→Groq | text |
| Tool Use | llm_tools | qwen3→Groq | json |
| Vision | vision_analyze | moondream→Gemini | text |
| Image Gen | image_generate | ComfyCloud→Replicate | image_url |
| Video Gen | video_generate | ComfyCloud→Replicate | video_url |
| Music Gen | music_generate | Suno→HF AudioCraft | audio_url |
| Audio FX | audio_process | HF Demucs | stems |
| Cross-Modal | cross_modal | full pipeline | image+audio |
| Text Input | — | local | text passthrough |
| Output | — | local | result collector |

## Free Tier Limits (Monthly)

| Service | Limit | Reset |
|---------|-------|-------|
| Comfy Cloud | 400 credits | Monthly |
| Groq | 14,400 req/day | Daily |
| Gemini Flash | 1,500 req/day | Daily |
| Suno | 50 songs/day | Daily |
| OpenRouter :free | model-varies | — |
| HuggingFace Spaces | unlimited (queued) | — |
| Replicate | $5 credit | One-time |
| Kaggle GPU | 30hr/week (T4) | Weekly |

**Total GPU cost: $0/month**

## Integrating into Existing RAINGOD-ComfyUI-Integration

Add to `rain_backend.py`:
```python
from .dispatch_routes import router as dispatch_router
app.include_router(dispatch_router)
```

This adds:
- `POST /dispatch`          → node graph execution endpoint
- `GET  /dispatch/status`   → fleet health for the UI

## API Key Procurement (30 min, all free)

```powershell
# Part 1: Open all signup tabs
$urls = @{
  "Comfy Cloud"  = "https://comfy.org"
  "Groq"         = "https://console.groq.com"
  "Google AI"    = "https://aistudio.google.com"
  "Suno"         = "https://suno.com"
  "OpenRouter"   = "https://openrouter.ai"
  "HuggingFace"  = "https://huggingface.co/settings/tokens"
  "Replicate"    = "https://replicate.com"
  "Kaggle"       = "https://kaggle.com/settings"
}
foreach ($s in $urls.GetEnumerator()) { Start-Process $s.Value; Start-Sleep 2 }

# Part 2: Deploy all keys
./scripts/deploy_api_keys.ps1

# Part 3: Validate
python scripts/validate_keys.py
```
