"""RAINGOD — Dynamic ComfyUI Workflow Builder.

Replaces hardcoded node-graph dicts with a programmatic assembler.

Node numbering convention
-------------------------
"1"   → CheckpointLoaderSimple
"2"   → CLIPTextEncode (positive)
"3"   → CLIPTextEncode (negative)
"4"   → EmptyLatentImage (txt2img) / LoadImage (img2img)
"5"   → KSampler
"6"   → VAEDecode
"7"   → SaveImage
"8"   → LoraLoader         (optional)
"9"   → ImageScale         (optional)
"10"  → VAEEncode          (img2img only)
"20"  → UpscaleModelLoader (upscale pass)
"21"  → ImageUpscaleWithModel
"22"  → SaveImage (upscaled)

Public API
----------
WorkflowBuilder().build_txt2img(...)    → ComfyUI API workflow dict
WorkflowBuilder().build_img2img(...)    → ComfyUI API workflow dict
WorkflowBuilder().build_upscale_pass()  → extended workflow dict
WorkflowBuilder().from_template(...)    → loaded + patched JSON dict
WorkflowBuilder().list_templates()      → list of template stems
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .rain_backend_config import LoRAConfig

_DEFAULT_CHECKPOINT = os.environ.get(
    "RAINGOD_CHECKPOINT", "v1-5-pruned-emaonly.safetensors"
)
_WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"


class WorkflowBuilder:
    """Assemble ComfyUI API-format workflow dicts programmatically."""

    def __init__(
        self,
        checkpoint:    str              = _DEFAULT_CHECKPOINT,
        workflows_dir: Path | str | None = None,
    ) -> None:
        self.checkpoint    = checkpoint
        self.workflows_dir = Path(workflows_dir) if workflows_dir else _WORKFLOWS_DIR

    # ------------------------------------------------------------------
    # Public builders
    # ------------------------------------------------------------------

    def build_txt2img(
        self,
        positive:         str,
        negative:         str,
        width:            int,
        height:           int,
        steps:            int,
        cfg:              float,
        sampler_name:     str,
        scheduler:        str,
        seed:             int,
        denoise:          float       = 1.0,
        batch_size:       int         = 1,
        lora:             LoRAConfig | None = None,
        checkpoint:       str | None  = None,
        filename_prefix:  str         = "raingod",
    ) -> dict[str, Any]:
        ckpt  = checkpoint or self.checkpoint
        graph: dict[str, Any] = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": ckpt},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive, "clip": ["1", 1]},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["1", 1]},
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": batch_size},
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model":        ["1", 0],
                    "positive":     ["2", 0],
                    "negative":     ["3", 0],
                    "latent_image": ["4", 0],
                    "seed":         seed,
                    "steps":        steps,
                    "cfg":          cfg,
                    "sampler_name": sampler_name,
                    "scheduler":    scheduler,
                    "denoise":      denoise,
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"images": ["6", 0], "filename_prefix": filename_prefix},
            },
        }

        if lora:
            graph = self._inject_lora(graph, lora)

        return graph

    def build_img2img(
        self,
        positive:         str,
        negative:         str,
        image_path:       str,
        steps:            int,
        cfg:              float,
        sampler_name:     str,
        scheduler:        str,
        seed:             int,
        denoise:          float       = 0.75,
        lora:             LoRAConfig | None = None,
        checkpoint:       str | None  = None,
        filename_prefix:  str         = "raingod_img2img",
    ) -> dict[str, Any]:
        ckpt  = checkpoint or self.checkpoint
        graph: dict[str, Any] = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": ckpt},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive, "clip": ["1", 1]},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["1", 1]},
            },
            "4": {
                "class_type": "LoadImage",
                "inputs": {"image": image_path, "upload": "image"},
            },
            "10": {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["4", 0], "vae": ["1", 2]},
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model":        ["1", 0],
                    "positive":     ["2", 0],
                    "negative":     ["3", 0],
                    "latent_image": ["10", 0],
                    "seed":         seed,
                    "steps":        steps,
                    "cfg":          cfg,
                    "sampler_name": sampler_name,
                    "scheduler":    scheduler,
                    "denoise":      denoise,
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"images": ["6", 0], "filename_prefix": filename_prefix},
            },
        }

        if lora:
            graph = self._inject_lora(graph, lora)

        return graph

    def build_upscale_pass(
        self,
        base_workflow:  dict[str, Any],
        upscale_model:  str = "4x-UltraSharp.pth",
    ) -> dict[str, Any]:
        graph = copy.deepcopy(base_workflow)
        graph["20"] = {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": upscale_model},
        }
        graph["21"] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["20", 0],
                "image":         ["6", 0],
            },
        }
        graph["22"] = {
            "class_type": "SaveImage",
            "inputs": {
                "images":          ["21", 0],
                "filename_prefix": "raingod_upscaled",
            },
        }
        return graph

    def from_template(
        self,
        template_name: str,
        patches:       dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load a JSON template and apply field-level patches.

        Patch keys use dotted notation: ``"<node_id>.<input_field>"``

        Example::

            wf = builder.from_template("txt2img_quality", patches={
                "2.text": "neon city at night",
                "5.seed": 42,
            })
        """
        template_path = self.workflows_dir / f"{template_name}.json"
        if not template_path.exists():
            raise FileNotFoundError(f"Workflow template not found: {template_path}")
        with template_path.open(encoding="utf-8") as fh:
            graph: dict[str, Any] = json.load(fh)

        if patches:
            graph = self._apply_patches(graph, patches)

        return graph

    def list_templates(self) -> list[str]:
        if not self.workflows_dir.exists():
            return []
        return sorted(p.stem for p in self.workflows_dir.iterdir() if p.suffix == ".json")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_lora(graph: dict[str, Any], lora: LoRAConfig) -> dict[str, Any]:
        graph = copy.deepcopy(graph)
        graph["8"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model":          ["1", 0],
                "clip":           ["1", 1],
                "lora_name":      lora.filename,
                "strength_model": lora.strength_model,
                "strength_clip":  lora.strength_clip,
            },
        }
        graph["5"]["inputs"]["model"] = ["8", 0]
        graph["2"]["inputs"]["clip"]  = ["8", 1]
        graph["3"]["inputs"]["clip"]  = ["8", 1]
        return graph

    @staticmethod
    def _apply_patches(
        graph:   dict[str, Any],
        patches: dict[str, Any],
    ) -> dict[str, Any]:
        graph = copy.deepcopy(graph)
        for dotted_path, value in patches.items():
            parts = dotted_path.split(".", 1)
            if len(parts) != 2:
                raise ValueError(
                    f"Patch key must be '<node_id>.<field>', got: {dotted_path!r}"
                )
            node_id, field_name = parts
            if node_id not in graph:
                raise ValueError(
                    f"Patch references non-existent node '{node_id}'. "
                    f"Available: {sorted(graph.keys())}"
                )
            graph[node_id]["inputs"][field_name] = value
        return graph
