# RAINGOD ComfyUI Integration — Architecture

> **Accuracy Notice**: This document reflects the **currently implemented** code.
> Features marked 🔲 Planned are not yet in the repository.

---

## System Overview

```
RAINGOD AI Music Kit
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ┌────────────────┐  HTTP  ┌──────────────────────────────┐   │
│  │ switchboard/   ├───────►│      FastAPI Backend         │   │
│  │ index.html     │        │      (rain_backend.py)       │   │
│  └────────────────┘        └─────────────┬────────────────┘   │
│                                          │                    │
│  ┌────────────────┐  HTTP                │ HTTP               │
│  │ examples/      ├─────────────────────►│                    │
│  │ generate_...py │                      │                    │
│  └────────────────┘              ┌───────▼────────┐          │
│                                  │   ComfyUI      │          │
│                                  │   :8188        │          │
│                                  └────────────────┘          │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Status

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| **Config** | `backend/rain_backend_config.py` | ✅ Implemented | Dataclasses, GPU detection, all presets |
| **ComfyUI Client** | `backend/comfyui_client.py` | ✅ Implemented | Circuit breaker, retry, dedup, polling |
| **FastAPI Backend** | `backend/rain_backend.py` | ✅ Implemented | 9 endpoints, Pydantic v2, lifespan |
| **Workflow Builder** | `backend/workflow_builder.py` | ✅ Implemented | txt2img, img2img, upscale, templates |
| **LoRA Manager** | `backend/lora_manager.py` | ✅ Implemented | Scan, load, chain, merge |
| **Album Art Example** | `examples/generate_album_art.py` | ✅ Implemented | Full CLI, 5 style presets |
| **Quickstart Script** | `scripts/rain_quickstart.sh` | ✅ Implemented | System checks, env setup |
| **Start All Script** | `scripts/start_all.sh` | ✅ Implemented | Service orchestration, PID tracking |
| **Docker** | `Dockerfile` | ✅ Implemented | Multi-stage, non-root user |
| **docker-compose** | `docker-compose.yml` | ✅ Implemented | ComfyUI + backend services |
| **CI Pipeline** | `.github/workflows/ci.yml` | ✅ Implemented | Lint/test/docker-build, SHA-pinned |
| **Switchboard UI** | `switchboard/index.html` | ✅ Implemented | Vanilla JS dashboard (6 panels) |
| **Workflow Templates** | `workflows/*.json` | ✅ Implemented | 5 JSON templates + README |
| **Test Suite** | `tests/` | ✅ Implemented | 184 tests (endpoints, CB, WB, LM) |
| **Audio-Visual Sync** | `backend/av_sync.py` | 🔲 Planned | Beat detection integration |

---

## Backend REST API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | — | Version and links |
| GET | `/health` | — | Backend + ComfyUI health status |
| GET | `/config` | — | Active configuration summary |
| GET | `/presets` | — | All resolution / sampler / LoRA presets |
| POST | `/generate` | — | Single image generation (async, 202) |
| POST | `/batch-generate` | — | Batch image generation (202) |
| GET | `/queue/status` | — | ComfyUI queue state |
| DELETE | `/queue/{prompt_id}` | — | Cancel a queued prompt |
| GET | `/outputs/{filename}` | — | Retrieve a generated file |

---

## Request Flow — Single Generation

```
Client
  │
  ├─ POST /generate  {prompt, preset, resolution, …}
  │     │
  │     ├─ Pydantic validation (GenerateRequest)
  │     ├─ Resolve SAMPLER_PRESETS[preset]
  │     ├─ Resolve RESOLUTION_PRESETS[resolution]
  │     ├─ WorkflowBuilder.build_txt2img(…)
  │     │     ├─ Assemble node graph (7–8 nodes)
  │     │     └─ Inject LoraLoader node if lora_style set
  │     ├─ ComfyUIClient.queue_prompt(workflow)
  │     │     ├─ CircuitBreaker.is_open() → fast-fail if OPEN
  │     │     ├─ SHA-256 dedup check (skip if already queued)
  │     │     ├─ POST /prompt → ComfyUI :8188
  │     │     └─ Return prompt_id
  │     └─ Return 202 GenerateResponse {prompt_id, job_id, …}
  │
  └─ GET /outputs/{filename}  (poll until image is ready)
```

---

## Circuit Breaker

`ComfyUIClient` embeds a three-state circuit breaker:

| State | Behaviour | Transition |
|-------|----------|------------|
| `CLOSED` | All requests pass through | → OPEN after 5 consecutive failures |
| `OPEN` | All requests rejected immediately (503) | → HALF_OPEN after 60 s |
| `HALF_OPEN` | One probe request allowed | → CLOSED on success; OPEN on failure |

---

## Workflow Builder

`WorkflowBuilder` (`backend/workflow_builder.py`) replaces the hardcoded
node-graph dict that previously lived inside `rain_backend.py`.

### Public Methods

| Method | Description |
|--------|-------------|
| `build_txt2img(…)` | Text-to-image workflow (7 nodes + optional LoRA) |
| `build_img2img(…)` | Image-to-image refinement (LoadImage + VAEEncode) |
| `build_upscale_pass(…)` | Append 2× upscale nodes to any existing workflow |
| `from_template(name, patches)` | Load a `workflows/<name>.json` and apply patches |
| `list_templates()` | List available JSON template stems |

### Node Numbering Convention

| Node ID | Class | Notes |
|---------|-------|-------|
| `"1"` | CheckpointLoaderSimple | Model + CLIP + VAE source |
| `"2"` | CLIPTextEncode | Positive conditioning |
| `"3"` | CLIPTextEncode | Negative conditioning |
| `"4"` | EmptyLatentImage / LoadImage | Latent source |
| `"5"` | KSampler | Denoising step |
| `"6"` | VAEDecode | Latent → pixel |
| `"7"` | SaveImage | Output saver |
| `"8"` | LoraLoader | Optional single LoRA |
| `"10"` | VAEEncode | img2img only |
| `"20–22"` | Upscale chain | Optional upscale pass |
| `"100+"` | LoraLoader chain | Multi-LoRA via `LoRAManager.build_lora_chain()` |

---

## LoRA Manager

`LoRAManager` (`backend/lora_manager.py`) provides:

- **Registry seeding** from static `LORA_MAPPINGS` config
- **Filesystem scan** (`scan()`) for new `.safetensors` / `.ckpt` files
- **`get(name)` / `load(name)`** — resolve by logical name
- **`build_lora_chain(graph, loras)`** — inject N LoRAs in sequence
- **`build_loader_node(name)`** — single-LoRA `inputs` dict
- **`merge_configs(*loras, blend_mode)`** — average / max / sum-clamp blend
- **`as_dict()` / `summary()`** — JSON-serialisable export

---

## Workflow Templates

Five production-ready templates ship in `workflows/`:

| File | Quality | Resolution | Steps | Notes |
|------|---------|-----------|-------|-------|
| `txt2img_draft.json` | Draft | 512×512 | 20 | Fastest preview |
| `txt2img_quality.json` | Standard | 1024×1024 | 40 | Default |
| `txt2img_final.json` | Final | 2048×2048 | 80 | Maximum quality |
| `img2img_refine.json` | Standard | source | 30 | 75% denoise |
| `txt2img_synthwave_lora.json` | Standard | 1024×1024 | 40 | Synthwave LoRA |

Load and patch templates via:
```python
wf = WorkflowBuilder().from_template("txt2img_quality", patches={
    "2.text": "my positive prompt",
    "5.seed": 42,
})
```

---

## Switchboard UI

`switchboard/index.html` is a self-contained vanilla-JS dashboard with:

| Panel | Purpose |
|-------|---------|
| **Dashboard** | Live health status, GPU tier, queue depth, activity log |
| **Generate** | Form with prompt, preset/resolution/LoRA chip selectors |
| **Queue** | Running + pending table with per-item cancel buttons |
| **Presets** | Tables of all sampler, resolution, and LoRA presets |
| **Config** | Edit API base URL; view live backend config JSON |
| **API Logs** | Timestamped log of all API calls made by the UI |

---

## CORS Configuration

The backend uses **environment-variable-driven** CORS.
`allow_origins=["*"]` is **no longer the default**:

```bash
# Development
export ALLOWED_ORIGINS="http://localhost:3000"

# Production (comma-separated)
export ALLOWED_ORIGINS="https://raingod.app,https://api.raingod.app"

uvicorn backend.rain_backend:app --host 0.0.0.0 --port 8000
```

If `ALLOWED_ORIGINS` is unset, the backend restricts CORS to
`http://localhost:3000` and logs a warning.

---

## Security Notes

- **CORS**: Now restricted via `ALLOWED_ORIGINS` env var (default: localhost:3000 only)
- **Path traversal**: `GET /outputs/{filename}` uses `Path.resolve()` comparison
  to prevent `../` escapes outside the `outputs/` directory
- **Docker**: Runs as non-root user `raingod` (UID 1000)
- **Secrets**: `.env` files excluded by `.gitignore`; never commit credentials

---

## Known Issues

### 12 MB GIF in Git History

`DEVIANT2026_small.gif` (12,109,044 bytes) is committed directly to Git.
This bloats every clone.  Migrate to Git LFS:

```bash
git lfs install
git lfs track "*.gif"
git add .gitattributes
git rm --cached DEVIANT2026_small.gif
git add DEVIANT2026_small.gif
git commit -m "chore: migrate DEVIANT2026_small.gif to Git LFS"
git push
```

Alternatively, host the GIF on a CDN and update the `<img>` tag in `README.md`.
