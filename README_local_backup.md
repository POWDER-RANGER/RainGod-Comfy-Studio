# 🌧️ RainGod Comfy Studio

> Node-based AI creative pipeline — local Ollama fleet + free cloud GPU fleet.
> Build cross-modal art: concept → image → vision analysis → music.

---

## Stack

| Layer       | Models / Services                                     | Cost     |
|-------------|-------------------------------------------------------|----------|
| Local LLM   | dolphin-llama3:8b, qwen3:4b, deepseek-r1:1.5b         | Free     |
| Local Vision| moondream:1.8b, nomic-embed-text                      | Free     |
| Image GPU   | Comfy Cloud (RTX Pro 6000, 400 credits/mo)            | Free     |
| Music       | Suno (50 songs/day)                                   | Free     |
| Audio FX    | HuggingFace Demucs/AudioCraft Spaces                  | Free     |
| LLM Cloud   | Groq (14,400 req/day), OpenRouter (300+ free models)  | Free     |
| Vision Cloud| Gemini Flash (1,500 req/day)                          | Free     |
| Overflow GPU| Replicate (\ one-time credit)                       | ~Free    |
| **Total**   |                                                       | **\/mo** |

---

## Quick Start

\\\powershell
# 1. Deploy all API keys (one-time)
.\deploy_raingod.ps1

# 2. Validate the fleet
python backend\validate_keys.py

# 3. Launch everything
.\start_all.ps1
\\\

Then open: **http://localhost:8000**

---

## File Structure

\\\
RAINGOD Studio/
├── start_all.ps1              # One-click boot
├── deploy_raingod.ps1         # API key deployment
├── .env.example               # Key template — copy to .env
├── README.md                  # This file
├── STUDIO_ARCHITECTURE.md     # Full system design
├── PROJECT_AUDIT.md           # File map & known issues
├── requirements.txt           # Python deps
│
├── switchboard/
│   └── index.html             # Node-graph studio UI
│
├── backend/
│   ├── main.py                # FastAPI entry point
│   ├── dispatcher.py          # Core routing engine
│   ├── dispatch_routes.py     # /dispatch API endpoints
│   ├── comfyui_client.py      # Local ComfyUI fallback
│   ├── workflow_builder.py    # ComfyUI graph assembler
│   ├── local_adapters/
│   │   └── ollama_adapter.py  # Local Ollama
│   ├── cloud_adapters/        # 7 cloud service adapters
│   └── workflows/             # ComfyUI JSON templates
│
├── scripts/
│   ├── validate_keys.py       # Fleet health check
│   └── deploy_raingod.ps1     # Key deployment
│
├── skills/                    # Skill customization Markdown files
└── docs/                      # Session history / internal docs
\\\

---

## Docs

- [Architecture](STUDIO_ARCHITECTURE.md)
- [Audit / Issue Tracker](PROJECT_AUDIT.md)
- [Skills Index](skills/SKILLS_INDEX.md)
- [API Docs](http://localhost:8000/api/docs) ← when server is running
