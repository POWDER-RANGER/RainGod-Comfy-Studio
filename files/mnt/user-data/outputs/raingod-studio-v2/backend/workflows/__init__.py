"""Backend workflow registry — loads JSON templates from /workflows/."""

from __future__ import annotations

import json
from pathlib import Path

_WF_DIR = Path(__file__).parent.parent.parent / "workflows"


def _load(name: str) -> dict:
    path = _WF_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow template not found: {path}")
    with open(path) as f:
        return json.load(f)


def _cached(name: str) -> dict:
    """Lazy-load and cache workflow templates."""
    if name not in _cache:
        _cache[name] = _load(name)
    return _cache[name]


_cache: dict[str, dict] = {}

# Public names — import these in adapters
@property
def ANIMATEDIFF_WORKFLOW() -> dict:  # type: ignore[misc]
    return _cached("animatediff")


# Make module-level access work via direct import
import importlib, sys

class _WorkflowModule(sys.modules[__name__].__class__):
    @property
    def ANIMATEDIFF_WORKFLOW(self) -> dict:
        return _cached("animatediff")


sys.modules[__name__].__class__ = _WorkflowModule
