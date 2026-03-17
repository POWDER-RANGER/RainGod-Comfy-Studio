"""RAINGOD — Dynamic ComfyUI Workflow Builder.

Replaces the hardcoded node-graph dict that previously lived inside
``rain_backend.py``.  All workflow assembly logic lives here so that
route handlers remain thin.

Node numbering convention
-------------------------
All node IDs are string keys per the ComfyUI API format::

    "1"  → CheckpointLoaderSimple
    "2"  → CLIPTextEncode (positive)
    "3"  → CLIPTextEncode (negative)
    "4"  → EmptyLatentImage (txt2img) / LoadImage (img2img)
    "5"  → KSampler
    "6"  → VAEDecode
    "7"  → SaveImage
    "8"  → LoraLoader         (optional — injected when lora is supplied)
    "9"  → ImageScale         (optional — upscale pass)
    "10" → VAEEncode          (img2img only)
    "20" → UpscaleModelLoader (build_upscale_pass)
    "21" → ImageUpscaleWithModel
    "22" → SaveImage (upscaled)

Connections between nodes use the ComfyUI *link* format:
``["<node_id>", <output_slot_index>]``

Public API
----------
``WorkflowBuilder().build_txt2img(...)``    → ComfyUI API workflow dict
``WorkflowBuilder().build_img2img(...)``    → ComfyUI API workflow dict
``WorkflowBuilder().build_upscale_pass()`` → extended workflow dict
``WorkflowBuilder().from_template(...)``    → loaded + patched JSON dict
``WorkflowBuilder().list_templates()``      → list of template stems
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .rain_backend_config import LoRAConfig

# Default checkpoint — override via RAINGOD_CHECKPOINT env var
_DEFAULT_CHECKPOINT = os.environ.get(
    "RAINGOD_CHECKPOINT", "v1-5-pruned-emaonly.safetensors"
)

# Directory containing exported ComfyUI JSON templates
_WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"


class WorkflowBuilder:
    """Assemble ComfyUI API-format workflow dicts programmatically.

    Every public method returns a *new* dict so callers can safely mutate
    the result without affecting future builds.

    Parameters
    ----------
    checkpoint:
        Default checkpoint filename (can be overridden per call via the
        ``checkpoint`` keyword argument on each builder method).
    workflows_dir:
        Directory to search for JSON template files.  Defaults to
        ``<repo-root>/workflows/``.
    """

    def __init__(
        self,
        checkpoint: str = _DEFAULT_CHECKPOINT,
        workflows_dir: Path | str | None = None,
    ) -> None:
        self.checkpoint = checkpoint
        self.workflows_dir = Path(workflows_dir) if workflows_dir else _WORKFLOWS_DIR

    # ------------------------------------------------------------------
    # Public builders
    # ------------------------------------------------------------------

    def build_txt2img(
        self,
        positive: str,
        negative: str,
        width: int,
        height: int,
        steps: int,
        cfg: float,
        sampler_name: str,
        scheduler: str,
        seed: int,
        denoise: float = 1.0,
        batch_size: int = 1,
        lora: LoRAConfig | None = None,
        checkpoint: str | None = None,
        filename_prefix: str = "raingod",
    ) -> dict[str, Any]:
        """Build a text-to-image workflow.

        Parameters
        ----------
        positive:
            Positive prompt text.
        negative:
            Negative prompt text.
        width, height:
            Output image dimensions in pixels (should be multiples of 64).
        steps:
            Number of KSampler denoising steps.
        cfg:
            Classifier-free guidance scale.
        sampler_name:
            ComfyUI sampler identifier, e.g. ``"dpmpp_2m"``.
        scheduler:
            ComfyUI scheduler name, e.g. ``"karras"``.
        seed:
            RNG seed for reproducibility.
        denoise:
            KSampler denoise strength (``1.0`` = full denoising).
        batch_size:
            Number of images in a single latent batch.
        lora:
            Optional :class:`~rain_backend_config.LoRAConfig` to inject.
        checkpoint:
            Override the instance-level default checkpoint filename.
        filename_prefix:
            Prefix for saved output filenames.

        Returns
        -------
        dict
            ComfyUI API-format workflow ready for
            ``ComfyUIClient.queue_prompt()``.
        """
        ckpt = checkpoint or self.checkpoint
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
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": batch_size,
                },
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "denoise": denoise,
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["6", 0],
                    "filename_prefix": filename_prefix,
                },
            },
        }

        if lora:
            graph = self._inject_lora(graph, lora)

        return graph

    def build_img2img(
        self,
        positive: str,
        negative: str,
        image_path: str,
        steps: int,
        cfg: float,
        sampler_name: str,
        scheduler: str,
        seed: int,
        denoise: float = 0.75,
        lora: LoRAConfig | None = None,
        checkpoint: str | None = None,
        filename_prefix: str = "raingod_img2img",
    ) -> dict[str, Any]:
        """Build an image-to-image (img2img) refinement workflow.

        The source image is loaded via ``LoadImage`` and encoded into the
        latent space with ``VAEEncode`` before the KSampler pass.

        Parameters
        ----------
        image_path:
            Filename of the source image as known to ComfyUI's input
            directory (not a local filesystem path).
        denoise:
            Denoising strength — lower values preserve more of the source
            image (``0.0`` = no change, ``1.0`` = full re-generation).
        """
        ckpt = checkpoint or self.checkpoint
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
            # Node 4: load source image
            "4": {
                "class_type": "LoadImage",
                "inputs": {"image": image_path, "upload": "image"},
            },
            # Node 10: encode pixels → latent
            "10": {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["4", 0], "vae": ["1", 2]},
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["10", 0],  # from VAEEncode
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "denoise": denoise,
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["6", 0],
                    "filename_prefix": filename_prefix,
                },
            },
        }

        if lora:
            graph = self._inject_lora(graph, lora)

        return graph

    def build_upscale_pass(
        self,
        base_workflow: dict[str, Any],
        upscale_model: str = "4x-UltraSharp.pth",
    ) -> dict[str, Any]:
        """Append a model-upscale pass to an existing workflow.

        Adds ``UpscaleModelLoader``, ``ImageUpscaleWithModel``, and a second
        ``SaveImage`` node after the primary VAEDecode output (node "6").

        Parameters
        ----------
        base_workflow:
            An existing workflow dict (output of ``build_txt2img`` or
            ``build_img2img``).  **Not mutated — a deep copy is returned.**
        upscale_model:
            Filename of the upscale model as known to ComfyUI
            (e.g. ``"4x-UltraSharp.pth"``).

        Returns
        -------
        dict
            A *copy* of the base workflow with upscale nodes appended at
            IDs "20", "21", "22".
        """
        graph = copy.deepcopy(base_workflow)
        graph["20"] = {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": upscale_model},
        }
        graph["21"] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["20", 0],
                "image": ["6", 0],  # VAEDecode output
            },
        }
        graph["22"] = {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["21", 0],
                "filename_prefix": "raingod_upscaled",
            },
        }
        return graph

    def from_template(
        self,
        template_name: str,
        patches: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load a JSON template and apply field-level patches.

        Template files live in ``self.workflows_dir`` with a ``.json``
        extension.  *patches* is a flat mapping of
        ``"<node_id>.<input_key>"`` → value applied after loading.

        Parameters
        ----------
        template_name:
            Filename stem without ``.json``, e.g. ``"txt2img_quality"``.
        patches:
            Optional flat dict of dotted-path overrides::

                {
                    "2.text": "positive prompt text",
                    "3.text": "negative prompt",
                    "5.seed": 42,
                }

        Returns
        -------
        dict
            Patched workflow ready for ``ComfyUIClient.queue_prompt()``.

        Raises
        ------
        FileNotFoundError
            If no matching ``.json`` template exists.
        ValueError
            If a patch path references a non-existent node or uses
            bad syntax.
        """
        template_path = self.workflows_dir / f"{template_name}.json"
        if not template_path.exists():
            raise FileNotFoundError(
                f"Workflow template not found: {template_path}"
            )
        with template_path.open(encoding="utf-8") as fh:
            graph: dict[str, Any] = json.load(fh)

        if patches:
            graph = self._apply_patches(graph, patches)

        return graph

    def list_templates(self) -> list[str]:
        """Return the stems of all available ``.json`` template files."""
        if not self.workflows_dir.exists():
            return []
        return sorted(
            p.stem
            for p in self.workflows_dir.iterdir()
            if p.suffix == ".json"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_lora(
        graph: dict[str, Any],
        lora: LoRAConfig,
    ) -> dict[str, Any]:
        """Insert a ``LoraLoader`` node (ID "8") and re-wire connections.

        The KSampler model input and both CLIPTextEncode clip inputs are
        re-pointed through the LoRA node outputs.

        Returns a deep copy — the original graph is never mutated.
        """
        graph = copy.deepcopy(graph)
        graph["8"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["1", 0],
                "clip": ["1", 1],
                "lora_name": lora.filename,
                "strength_model": lora.strength_model,
                "strength_clip": lora.strength_clip,
            },
        }
        # KSampler: model ← LoraLoader output 0
        graph["5"]["inputs"]["model"] = ["8", 0]
        # Positive CLIP encoder: clip ← LoraLoader output 1
        graph["2"]["inputs"]["clip"] = ["8", 1]
        # Negative CLIP encoder: clip ← LoraLoader output 1
        graph["3"]["inputs"]["clip"] = ["8", 1]
        return graph

    @staticmethod
    def _apply_patches(
        graph: dict[str, Any],
        patches: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply ``"<node_id>.<input_field>"`` patches to a graph copy.

        Raises
        ------
        ValueError
            If a key does not contain exactly one dot, or references a
            node that does not exist in the graph.
        """
        graph = copy.deepcopy(graph)
        for dotted_path, value in patches.items():
            parts = dotted_path.split(".", 1)
            if len(parts) != 2:
                raise ValueError(
                    f"Patch key must be '<node_id>.<field>', got: {dotted_path!r}"
                )
            node_id, field = parts
            if node_id not in graph:
                raise ValueError(
                    f"Patch references non-existent node '{node_id}'. "
                    f"Available: {sorted(graph.keys())}"
                )
            graph[node_id]["inputs"][field] = value
        return graph
