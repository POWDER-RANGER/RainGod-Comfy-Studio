"""RAINGOD — LoRA Manager.

Provides filesystem scanning and runtime management of LoRA weight files.

Public API
----------
LoRAManager.scan()              → refresh available LoRA list
LoRAManager.available()         → list available LoRA names
LoRAManager.get(name)           → LoRAConfig | None
LoRAManager.load(name)          → LoRAConfig (raises if not found)
LoRAManager.build_lora_chain()  → inject multi-LoRA nodes into a workflow
LoRAManager.build_loader_node() → ComfyUI LoraLoader inputs dict
LoRAManager.merge_configs()     → blend multiple LoRAConfigs
LoRAManager.as_dict()           → JSON-serialisable registry dump
LoRAManager.summary()           → full summary with disk info
"""

from __future__ import annotations

import copy
import logging
import os
import re
from pathlib import Path
from typing import Any

from .rain_backend_config import LORA_MAPPINGS, LoRAConfig

logger = logging.getLogger(__name__)

_LORA_EXTENSIONS: frozenset[str] = frozenset({
    ".safetensors", ".ckpt", ".pt", ".bin", ".pth"
})

_DEFAULT_LORA_DIR = Path(
    os.environ.get(
        "RAINGOD_LORA_DIR",
        str(Path(__file__).parent.parent / "loras"),
    )
)

_DEFAULT_STRENGTH = 0.8


class LoRANotFoundError(KeyError):
    """Raised when a requested LoRA is not found in the registry."""


class LoRAManager:
    """Manages available LoRA files and their configuration."""

    def __init__(self, lora_dir: Path | str | None = None) -> None:
        self._lora_dir = Path(lora_dir) if lora_dir else _DEFAULT_LORA_DIR
        self._registry: dict[str, LoRAConfig] = {}
        self._seed_from_config()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _seed_from_config(self) -> None:
        for name, cfg in LORA_MAPPINGS.items():
            self._registry[name] = cfg
        logger.debug("LoRAManager seeded %d entries from LORA_MAPPINGS", len(self._registry))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> list[str]:
        """Scan lora_dir and refresh the registry with newly discovered files."""
        if not self._lora_dir.exists():
            logger.warning(
                "LoRA directory does not exist: %s — using config-only registry",
                self._lora_dir,
            )
            return sorted(self._registry.keys())

        existing_filenames = {cfg.filename for cfg in self._registry.values()}
        discovered = 0

        for path in self._lora_dir.iterdir():
            if path.suffix.lower() not in _LORA_EXTENSIONS:
                continue
            if not path.is_file():
                continue
            if path.name in existing_filenames:
                continue

            stem = _stem_to_slug(path.stem)
            if stem not in self._registry:
                self._registry[stem] = LoRAConfig(
                    filename=path.name,
                    strength_model=_DEFAULT_STRENGTH,
                    strength_clip=_DEFAULT_STRENGTH,
                    description=f"Auto-discovered: {path.name}",
                )
                discovered += 1

        if discovered:
            logger.info("LoRAManager discovered %d new LoRA(s) in %s", discovered, self._lora_dir)

        return sorted(self._registry.keys())

    def available(self) -> list[str]:
        return sorted(self._registry.keys())

    def get(self, name: str) -> LoRAConfig | None:
        return self._registry.get(name)

    def load(self, name: str) -> LoRAConfig:
        cfg = self._registry.get(name)
        if cfg is None:
            raise LoRANotFoundError(
                f"LoRA '{name}' not found. Available: {sorted(self._registry.keys())}"
            )
        return cfg

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "filename":       cfg.filename,
                "strength_model": cfg.strength_model,
                "strength_clip":  cfg.strength_clip,
                "description":    cfg.description,
            }
            for name, cfg in sorted(self._registry.items())
        }

    def build_lora_chain(
        self,
        graph: dict[str, Any],
        loras: list[tuple[str, float, float]],
    ) -> dict[str, Any]:
        """Inject a chain of LoRA loaders into an existing workflow.

        Each LoRA feeds its model/clip outputs into the next, forming a
        sequential blend. Node IDs start at ``"100"`` to avoid collisions.

        Parameters
        ----------
        graph:
            Base workflow dict — **not mutated**, a deep copy is returned.
        loras:
            Ordered list of ``(name, strength_model, strength_clip)`` tuples.
        """
        if not loras:
            raise ValueError("loras list must not be empty")

        graph = copy.deepcopy(graph)
        base_node_id   = 100
        prev_model_ref: list[Any] = ["1", 0]
        prev_clip_ref:  list[Any] = ["1", 1]

        for idx, (name, strength_model, strength_clip) in enumerate(loras):
            cfg     = self.load(name)
            node_id = str(base_node_id + idx)

            graph[node_id] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "model":          prev_model_ref,
                    "clip":           prev_clip_ref,
                    "lora_name":      cfg.filename,
                    "strength_model": strength_model,
                    "strength_clip":  strength_clip,
                },
            }

            prev_model_ref = [node_id, 0]
            prev_clip_ref  = [node_id, 1]

        graph["5"]["inputs"]["model"] = prev_model_ref
        graph["2"]["inputs"]["clip"]  = prev_clip_ref
        graph["3"]["inputs"]["clip"]  = prev_clip_ref

        return graph

    def build_loader_node(
        self,
        name:           str,
        strength_model: float | None = None,
        strength_clip:  float | None = None,
    ) -> dict[str, Any]:
        cfg = self.load(name)
        return {
            "lora_name":      cfg.filename,
            "strength_model": strength_model if strength_model is not None else cfg.strength_model,
            "strength_clip":  strength_clip  if strength_clip  is not None else cfg.strength_clip,
        }

    @staticmethod
    def merge_configs(
        *loras:     LoRAConfig,
        blend_mode: str = "average",
    ) -> LoRAConfig:
        """Blend multiple LoRAConfig entries.

        blend_mode options: ``"average"``, ``"max"``, ``"sum_clamp"``
        """
        if len(loras) < 2:
            raise ValueError("merge_configs requires at least 2 LoRAConfig entries")

        valid_modes = {"average", "max", "sum_clamp"}
        if blend_mode not in valid_modes:
            raise ValueError(
                f"Unknown blend_mode {blend_mode!r}. Choose from: {valid_modes}"
            )

        model_strengths = [lo.strength_model for lo in loras]
        clip_strengths  = [lo.strength_clip  for lo in loras]

        if blend_mode == "average":
            sm = sum(model_strengths) / len(model_strengths)
            sc = sum(clip_strengths)  / len(clip_strengths)
        elif blend_mode == "max":
            sm = max(model_strengths)
            sc = max(clip_strengths)
        else:  # sum_clamp
            sm = min(sum(model_strengths), 1.0)
            sc = min(sum(clip_strengths),  1.0)

        return LoRAConfig(
            filename="+".join(lo.filename for lo in loras),
            strength_model=round(sm, 4),
            strength_clip=round(sc, 4),
            description="Blended: " + ", ".join(
                lo.description or lo.filename for lo in loras
            ),
        )

    def summary(self) -> dict[str, Any]:
        entries = self.as_dict()
        return {
            "lora_dir": str(self._lora_dir),
            "total":    len(entries),
            "loras":    entries,
        }

    @property
    def lora_dir(self) -> Path:
        return self._lora_dir

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, name: object) -> bool:
        return name in self._registry

    def __repr__(self) -> str:
        return (
            f"LoRAManager(lora_dir={self._lora_dir!r}, "
            f"registered={len(self._registry)})"
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _stem_to_slug(stem: str) -> str:
    """Convert a filename stem to a lowercase API-friendly slug.

    Examples
    --------
    ``"synthwave_v2"``       → ``"synthwave_v2"``
    ``"My LoRA File (v3)"``  → ``"my_lora_file_v3"``
    """
    slug = stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")
