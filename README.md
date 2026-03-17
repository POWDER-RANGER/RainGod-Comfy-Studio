# ⚡ RainGod Comfy Studio

> **Production-grade AI music visual generation studio — node-based workflow engine + ComfyUI backend**

[![CI](https://github.com/POWDER-RANGER/RainGod-Comfy-Studio/actions/workflows/ci.yml/badge.svg)](https://github.com/POWDER-RANGER/RainGod-Comfy-Studio/actions/workflows/ci.yml)
[![Security Scans](https://github.com/POWDER-RANGER/RainGod-Comfy-Studio/actions/workflows/security.yml/badge.svg)](https://github.com/POWDER-RANGER/RainGod-Comfy-Studio/actions/workflows/security.yml)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Integration-green.svg)](https://github.com/comfyanonymous/ComfyUI)

---

## 🎯 Overview

RainGod Comfy Studio is the unified visual generation engine and workflow interface for the **RAINGOD AI Music Kit** — combining a node-based studio frontend with a production-grade FastAPI backend wired directly into ComfyUI.

Built by **Curtis Charles Farrar** ([@POWDER-RANGER](https://github.com/POWDER-RANGER)) | ORCID: [0009-0008-9273-2458](https://orcid.org/0009-0008-9273-2458)

---

## 🏗️ Architecture

```
RainGod Comfy Studio
├── switchboard/          ← Vanilla JS dashboard (6 panels, live health/queue/generation)
├── backend/              ← FastAPI backend
│   ├── rain_backend.py       REST API (9 endpoints)
│   ├── comfyui_client.py     Circuit breaker + retry + dedup
│   ├── workflow_builder.py   Dynamic ComfyUI graph assembly
│   ├── lora_manager.py       LoRA scan/load/chain/merge
│   └── rain_backend_config.py  All presets + GPU detection
├── workflows/            ← ComfyUI JSON templates (8 presets)
├── files/                ← Multi-provider adapters
│   ├── gemini_adapter.py     Google Gemini
│   ├── groq_adapter.py       Groq LLM
│   ├── suno_adapter.py       Suno music generation
│   ├── replicate_adapter.py  Replicate inference
│   ├── ollama_adapter.py     Local Ollama
│   ├── hf_adapter.py         HuggingFace
│   ├── dispatcher.py         Multi-provider routing
│   └── comfy_cloud_adapter.py  Cloud ComfyUI
├── skills/               ← Agent skill definitions (7 skills)
├── tests/                ← 184 pytest tests
├── scripts/              ← quickstart + start_all
├── examples/             ← Album art generation CLI
└── docs/                 ← Architecture docs
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/POWDER-RANGER/RainGod-Comfy-Studio.git
cd RainGod-Comfy-Studio
chmod +x scripts/rain_quickstart.sh
./scripts/rain_quickstart.sh
```

Or manually:

```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.rain_backend:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/docs` for the API or `switchboard/index.html` in your browser for the dashboard.

---

## 🔧 Backend API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Backend + ComfyUI status |
| GET | `/presets` | All sampler/resolution/LoRA presets |
| POST | `/generate` | Single image generation (async, 202) |
| POST | `/batch-generate` | Batch generation |
| GET | `/queue/status` | ComfyUI queue state |
| DELETE | `/queue/{id}` | Cancel queued prompt |
| GET | `/outputs/{filename}` | Retrieve generated file |

---

## 🎨 Workflow Templates

| Template | Steps | Resolution | Notes |
|----------|-------|-----------|-------|
| `txt2img_draft` | 20 | 512×512 | Fastest preview |
| `txt2img_quality` | 40 | 1024×1024 | Default production |
| `txt2img_final` | 80 | 2048×2048 | Maximum quality |
| `txt2img_ultra` | 80 | 2048×2048 | Ultra sampler |
| `txt2img_synthwave_lora` | 40 | 1024×1024 | Synthwave LoRA |
| `img2img_refine` | 30 | source | 75% denoise |

---

## 🔌 Provider Adapters (`files/`)

| Adapter | Provider | Use Case |
|---------|----------|----------|
| `gemini_adapter.py` | Google Gemini | Prompt generation / vision |
| `groq_adapter.py` | Groq | Fast LLM inference |
| `suno_adapter.py` | Suno | AI music generation |
| `replicate_adapter.py` | Replicate | Remote model inference |
| `ollama_adapter.py` | Ollama | Local LLM |
| `hf_adapter.py` | HuggingFace | Model hub inference |
| `comfy_cloud_adapter.py` | ComfyUI Cloud | Remote ComfyUI |

---

## 🧪 Testing

```bash
pip install pytest pytest-cov
pytest tests/ --verbose --cov=backend --cov-report=term-missing
```

184 tests across: API endpoints, circuit breaker, workflow builder, LoRA manager.

---

## 🐳 Docker

```bash
docker-compose up -d
```

Services: ComfyUI (:8188) + RAINGOD backend (:8000) + Redis + Nginx reverse proxy.

---

## 📁 Windows Quick Launch

```powershell
.\start_all.ps1
```

---

## 🔐 Security

- All GitHub Actions SHA-pinned
- CodeQL + Bandit + OSV Scanner + DevSkim running on every push
- Dependabot configured for pip + actions updates
- CORS restricted via `ALLOWED_ORIGINS` env var
- Non-root Docker user
- Path traversal protection on `/outputs/` endpoint

---

## 📚 Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Full system architecture
- [`INSTALLATION.md`](INSTALLATION.md) — Setup guide
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Contribution guidelines
- [`CONTACT.md`](CONTACT.md) — Contact & support

---

## ⚖️ License

MIT — see [LICENSE](LICENSE). Attribution required.  
**Curtis Charles Farrar** | ORCID: [0009-0008-9273-2458](https://orcid.org/0009-0008-9273-2458)
