"""RAINGOD FastAPI Backend.

Provides a REST API over ComfyUI for the RAINGOD AI Music Kit visual
generation pipeline.

Endpoints
---------
GET  /                   Root / version info
GET  /health             Health check (backend + ComfyUI upstream)
GET  /config             Configuration summary
GET  /presets            All available presets
POST /generate           Single image generation
POST /batch-generate     Batch image generation
GET  /queue/status       ComfyUI queue state
DEL  /queue/{prompt_id}  Cancel a queued prompt
GET  /outputs/{filename} Retrieve a generated image file
"""

from __future__ import annotations

import logging
import mimetypes
import os
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi import Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from requests.exceptions import RequestException

from . import project_store
from .comfyui_client import ComfyUIClient
from .rain_backend_config import (
    LORA_MAPPINGS,
    RESOLUTION_PRESETS,
    SAMPLER_PRESETS,
    QualityTier,
)
from .rain_backend_config import config as rain_config
from .workflow_builder import WorkflowBuilder

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, rain_config.logging.level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def _single_line_log_value(value: object) -> str:
    """Escape line breaks before including untrusted values in log records."""
    return str(value).replace("\r", r"\r").replace("\n", r"\n")


# ---------------------------------------------------------------------------
# CORS — driven by ALLOWED_ORIGINS environment variable
#
# Production:  export ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
# Development: export ALLOWED_ORIGINS="http://localhost:3000"
#              (or leave unset — defaults to localhost:3000 with a warning)
# ---------------------------------------------------------------------------
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
if _raw_origins.strip():
    _allow_origins: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    # Safe development default — never silently allow everything in production
    _allow_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    logger.warning(
        "ALLOWED_ORIGINS env var not set — CORS restricted to %s. "
        "Set ALLOWED_ORIGINS=<comma-separated list> for production.",
        _allow_origins,
    )

# ---------------------------------------------------------------------------
# ComfyUI Client singleton & lifespan
# ---------------------------------------------------------------------------
client: ComfyUIClient | None = None
OUTPUT_DIR = Path("outputs")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan handler — initialise and tear down the ComfyUI client."""
    global client
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = ComfyUIClient()
    logger.info(
        "RAINGOD backend started — ComfyUI: %s — GPU: %s",
        rain_config.comfyui.base_url,
        rain_config.gpu_tier.value,
    )
    try:
        yield
    finally:
        active_client = client
        client = None
        if active_client is not None:
            active_client.close()
        logger.info("RAINGOD backend shutting down")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Rain God's Sad Boy Pipeline API",
    description="Artist-controlled creative generation API for Rain God's Sad Boy Pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


def _get_client() -> ComfyUIClient:
    if client is None:
        raise HTTPException(status_code=503, detail="Backend not initialised")
    return client


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096, description="Positive prompt")
    negative_prompt: str = Field(default="", description="Negative prompt")
    preset: str = Field(default="quality", description="Sampler preset key")
    resolution: str = Field(default="cover_art", description="Resolution preset key")
    lora_style: str | None = Field(default=None, description="LoRA style key")
    seed: int | None = Field(default=None, ge=0, description="Random seed")
    quality_tier: QualityTier = Field(default=QualityTier.STANDARD)
    metadata: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = Field(default=None, min_length=1, max_length=64)
    approved: bool = Field(
        default=False,
        description="Explicit approval required when recording this generation in a project",
    )


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class BatchGenerateRequest(BaseModel):
    requests: list[GenerateRequest] = Field(..., min_length=1, max_length=50)
    priority: str = Field(default="normal", description="Queue priority hint")


class GenerateResponse(BaseModel):
    prompt_id: str
    job_id: str
    status: str
    estimated_time: str
    preset_used: str
    resolution_used: dict[str, int]
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    comfyui_available: bool
    gpu_tier: str
    version: str
    uptime_seconds: float


# ---------------------------------------------------------------------------
# WorkflowBuilder singleton — used by /generate and /batch-generate
# ---------------------------------------------------------------------------
_workflow_builder = WorkflowBuilder()


# ---------------------------------------------------------------------------
# Application startup time (for uptime reporting)
# ---------------------------------------------------------------------------
_START_TIME = time.monotonic()


def _read_prompt_history(cl: ComfyUIClient, prompt_id: str) -> dict[str, Any]:
    """Read ComfyUI history and map upstream failures to an API error."""
    try:
        return cl.get_history(prompt_id)
    except (RequestException, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="ComfyUI history is currently unavailable",
        ) from exc


def _persist_provider_job_status(prompt_id: str, status: str) -> None:
    """Best-effort reconciliation; upstream status remains readable if local storage is down."""
    try:
        project_store.update_job_status_by_provider_id(prompt_id, status)
    except Exception:
        logger.exception("Could not reconcile local job status for prompt_id=%s", prompt_id)


def _history_images(history: dict[str, Any]) -> list[dict[str, str]]:
    """Extract safe image descriptors from a ComfyUI history record."""
    outputs = history.get("outputs", {})
    if not isinstance(outputs, dict):
        return []

    images: list[dict[str, str]] = []
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        node_images = node_output.get("images", [])
        if not isinstance(node_images, list):
            continue
        for item in node_images:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            if not isinstance(filename, str) or not filename:
                continue
            image_type = item.get("type", "output")
            if image_type not in {"output", "temp", "input"}:
                continue
            subfolder = item.get("subfolder", "")
            images.append(
                {
                    "filename": filename,
                    "subfolder": subfolder if isinstance(subfolder, str) else "",
                    "type": image_type,
                }
            )
    return images


def _queue_contains(items: Any, prompt_id: str) -> bool:
    """Recognize prompt IDs in ComfyUI's standard queue tuple or object forms."""
    if not isinstance(items, list):
        return False
    for item in items:
        if isinstance(item, dict) and item.get("prompt_id") == prompt_id:
            return True
        if isinstance(item, list | tuple) and len(item) > 1 and item[1] == prompt_id:
            return True
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", summary="Root")
async def root() -> dict[str, str]:
    return {
        "name": "Rain God's Sad Boy Pipeline API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    cl = _get_client()
    comfyui_ok = cl.health_check()
    return HealthResponse(
        status="healthy" if comfyui_ok else "degraded",
        comfyui_available=comfyui_ok,
        gpu_tier=rain_config.gpu_tier.value,
        version="1.0.0",
        uptime_seconds=time.monotonic() - _START_TIME,
    )


@app.get("/config", summary="Configuration summary")
async def get_config() -> dict[str, Any]:
    return {
        "comfyui_url": rain_config.comfyui.base_url,
        "gpu_tier": rain_config.gpu_tier.value,
        "resolution_presets": list(RESOLUTION_PRESETS.keys()),
        "sampler_presets": list(SAMPLER_PRESETS.keys()),
        "lora_styles": list(LORA_MAPPINGS.keys()),
        "batch_max_concurrent": rain_config.batch.max_concurrent,
        "cache_enabled": rain_config.cache.enabled,
    }


@app.get("/presets", summary="All presets")
async def get_presets() -> dict[str, Any]:
    return {
        "resolution": RESOLUTION_PRESETS,
        "samplers": {
            k: {
                "steps": v.steps,
                "cfg": v.cfg,
                "sampler_name": v.sampler_name,
                "scheduler": v.scheduler,
                "description": v.description,
            }
            for k, v in SAMPLER_PRESETS.items()
        },
        "lora": {
            k: {
                "filename": v.filename,
                "strength_model": v.strength_model,
                "description": v.description,
            }
            for k, v in LORA_MAPPINGS.items()
        },
        "quality_tiers": [t.value for t in QualityTier],
    }


@app.post("/generate", response_model=GenerateResponse, status_code=202)
async def generate(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
) -> GenerateResponse:
    """Submit a single image generation request to ComfyUI."""
    cl = _get_client()

    if req.project_id and not req.approved:
        raise HTTPException(
            status_code=400,
            detail="Set approved=true to record a generation under a project",
        )
    if req.project_id and project_store.get_project(req.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if req.preset not in SAMPLER_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {req.preset}")
    if req.resolution not in RESOLUTION_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown resolution: {req.resolution}")

    sampler = SAMPLER_PRESETS[req.preset]
    resolution = RESOLUTION_PRESETS[req.resolution]
    lora_cfg = LORA_MAPPINGS.get(req.lora_style) if req.lora_style else None
    seed = req.seed if req.seed is not None else int(uuid.uuid4().int % (2**32))

    workflow = _workflow_builder.build_txt2img(
        positive=req.prompt,
        negative=req.negative_prompt,
        width=resolution["width"],
        height=resolution["height"],
        steps=sampler.steps,
        cfg=sampler.cfg,
        sampler_name=sampler.sampler_name,
        scheduler=sampler.scheduler,
        seed=seed,
        lora=lora_cfg,
    )

    job_id = str(uuid.uuid4())
    if req.project_id:
        try:
            project_store.create_generation_job(
                project_id=req.project_id,
                job_id=job_id,
                request={
                    "prompt": req.prompt,
                    "negative_prompt": req.negative_prompt,
                    "preset": req.preset,
                    "resolution": req.resolution,
                    "lora_style": req.lora_style,
                    "quality_tier": req.quality_tier.value,
                    "metadata": req.metadata,
                },
                provenance={
                    "provider": "comfyui",
                    "workflow": "txt2img",
                    "workflow_version": 1,
                    "seed": seed,
                    "width": resolution["width"],
                    "height": resolution["height"],
                    "steps": sampler.steps,
                    "cfg": sampler.cfg,
                    "sampler_name": sampler.sampler_name,
                    "scheduler": sampler.scheduler,
                },
                approval={
                    "decision": "approved",
                    "policy_version": "local-project-generation-v1",
                    "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
        except Exception as exc:
            logger.exception("Could not persist project generation job")
            raise HTTPException(
                status_code=503, detail="Project job storage is unavailable"
            ) from exc

    try:
        prompt_id = cl.queue_prompt(workflow)
    except RuntimeError as exc:
        if req.project_id:
            project_store.update_generation_job(job_id, status="failed", error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if req.project_id:
        project_store.update_generation_job(job_id, status="queued", provider_job_id=prompt_id)

    estimated_steps = sampler.steps
    estimated_seconds = estimated_steps * 0.3  # rough estimate
    logger.info(
        "Generation queued job_id=%s prompt_id=%s preset=%s resolution=%s",
        job_id,
        _single_line_log_value(prompt_id),
        req.preset,
        req.resolution,
    )
    return GenerateResponse(
        prompt_id=prompt_id,
        job_id=job_id,
        status="queued",
        estimated_time=f"{estimated_seconds:.0f}s",
        preset_used=req.preset,
        resolution_used=resolution,
        metadata={**req.metadata, "seed": seed},
    )


@app.post("/projects", status_code=201, summary="Create a local creative project")
async def create_project(req: CreateProjectRequest) -> dict[str, Any]:
    """Create a project in the local SQLite development store."""
    try:
        return project_store.create_project(req.name.strip(), req.description.strip())
    except Exception as exc:
        logger.exception("Could not create project")
        raise HTTPException(status_code=503, detail="Project storage is unavailable") from exc


@app.get("/projects/{project_id}", summary="Read a project and its generation records")
async def read_project(
    project_id: Annotated[str, FPath(min_length=1, max_length=64)],
) -> dict[str, Any]:
    """Return project metadata and studio-owned job/provenance records."""
    try:
        project = project_store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        project["jobs"] = project_store.list_project_jobs(project_id)
        project["assets"] = project_store.list_project_assets(project_id)
        for asset in project["assets"]:
            asset["url"] = f"/projects/{project_id}/assets/{asset['id']}"
        return project
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Could not read project")
        raise HTTPException(status_code=503, detail="Project storage is unavailable") from exc


@app.get(
    "/projects/{project_id}/assets/{asset_id}",
    summary="Retrieve a locally persisted project image",
)
async def read_project_asset(
    project_id: Annotated[str, FPath(min_length=1, max_length=64)],
    asset_id: Annotated[str, FPath(min_length=1, max_length=64)],
) -> Response:
    """Read image bytes from local project storage rather than ComfyUI history."""
    try:
        asset, content = project_store.load_project_asset(project_id, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Project asset not found")
        assert content is not None
        return Response(
            content=content,
            media_type=asset["mime_type"],
            headers={"Cache-Control": "no-store"},
        )
    except HTTPException:
        raise
    except OSError as exc:
        logger.exception("Could not read local project asset")
        raise HTTPException(status_code=503, detail="Project asset storage is unavailable") from exc


@app.post("/batch-generate", status_code=202)
async def batch_generate(
    batch_req: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Submit multiple generation requests as a batch."""
    if len(batch_req.requests) > rain_config.batch.max_queue_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds max {rain_config.batch.max_queue_size}",
        )

    batch_id = str(uuid.uuid4())
    results = []

    for req in batch_req.requests:
        try:
            single_response = await generate(req, background_tasks)
            results.append({"status": "queued", "prompt_id": single_response.prompt_id})
        except HTTPException as exc:
            results.append({"status": "error", "detail": exc.detail})

    return {
        "batch_id": batch_id,
        "total": len(batch_req.requests),
        "queued": sum(1 for r in results if r["status"] == "queued"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }


@app.get("/queue/status", summary="ComfyUI queue status")
async def queue_status() -> dict[str, Any]:
    cl = _get_client()
    try:
        return cl.get_queue_status()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete("/queue/{prompt_id}", summary="Cancel a queued prompt")
async def cancel_queue_item(
    prompt_id: Annotated[str, FPath(description="prompt_id to cancel")],
) -> dict[str, Any]:
    cl = _get_client()
    cancelled = cl.cancel_prompt(prompt_id)
    return {"prompt_id": prompt_id, "cancelled": cancelled}


@app.get("/jobs/{prompt_id}", summary="Inspect a ComfyUI generation job")
async def get_job_status(
    prompt_id: Annotated[str, FPath(min_length=1, max_length=128)],
) -> dict[str, Any]:
    """Return real queue/history status and available images for a submitted prompt."""
    cl = _get_client()
    history = _read_prompt_history(cl, prompt_id)

    if history:
        upstream_status = history.get("status", {})
        if not isinstance(upstream_status, dict):
            upstream_status = {}
        if upstream_status.get("status_str") == "error":
            status = "error"
        elif upstream_status.get("completed"):
            status = "completed"
        else:
            status = str(upstream_status.get("status_str") or "running")
        _persist_provider_job_status(prompt_id, status)
        image_items = _history_images(history)
        return {
            "prompt_id": prompt_id,
            "status": status,
            "completed": bool(upstream_status.get("completed")),
            "images": [
                {"index": index, "url": f"/jobs/{prompt_id}/images/{index}"}
                for index in range(len(image_items))
            ],
        }

    try:
        queue = cl.get_queue_status()
    except (RequestException, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="ComfyUI queue status is currently unavailable",
        ) from exc

    if _queue_contains(queue.get("queue_running", []), prompt_id):
        status = "running"
    elif _queue_contains(queue.get("queue_pending", []), prompt_id):
        status = "queued"
    else:
        raise HTTPException(
            status_code=404,
            detail="Prompt was not found in ComfyUI history or queue",
        )

    _persist_provider_job_status(prompt_id, status)
    return {"prompt_id": prompt_id, "status": status, "completed": False, "images": []}


@app.get("/jobs/{prompt_id}/images/{image_index}", summary="Retrieve a generated ComfyUI image")
async def get_job_image(
    prompt_id: Annotated[str, FPath(min_length=1, max_length=128)],
    image_index: Annotated[int, FPath(ge=0, le=99)],
) -> Response:
    """Proxy a real image referenced by ComfyUI history; never invent a file path."""
    cl = _get_client()
    history = _read_prompt_history(cl, prompt_id)
    image_items = _history_images(history)
    if image_index >= len(image_items):
        raise HTTPException(status_code=404, detail="Image not found for this prompt")

    image = image_items[image_index]
    media_type = mimetypes.guess_type(image["filename"])[0] or "application/octet-stream"
    if not media_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="ComfyUI output is not a supported image")

    try:
        content = cl.get_image_bytes(
            image["filename"],
            subfolder=image["subfolder"],
            image_type=image["type"],
        )
    except (RequestException, RuntimeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve the generated image from ComfyUI",
        ) from exc

    try:
        asset = project_store.save_project_asset(prompt_id, image["filename"], media_type, content)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Could not persist generated project image")
        raise HTTPException(status_code=503, detail="Project asset storage is unavailable") from exc

    headers = {"Cache-Control": "no-store"}
    if asset is not None:
        headers["X-RainGod-Asset-ID"] = asset["id"]
    return Response(content=content, media_type=media_type, headers=headers)


@app.get("/outputs/{filename}", summary="Retrieve generated image")
async def get_output(
    filename: Annotated[str, FPath(description="Output filename")],
) -> FileResponse:
    path = OUTPUT_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    # Compare path components instead of string prefixes. A prefix check would
    # incorrectly allow sibling paths such as ``outputs-private/secret.png``.
    output_root = OUTPUT_DIR.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    return FileResponse(resolved)
