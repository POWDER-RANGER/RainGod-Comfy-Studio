"""Dispatch endpoints — /dispatch and /dispatch/status."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .dispatcher import RainGodDispatcher, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dispatch", tags=["dispatch"])
_dispatcher = RainGodDispatcher()


class DispatchRequest(BaseModel):
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    prefer_local: bool = True


@router.post("")
async def dispatch(req: DispatchRequest) -> dict[str, Any]:
    try:
        task = TaskType(req.task_type)
    except ValueError:
        valid_tasks = [task.value for task in TaskType]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task_type: {req.task_type}. Valid: {valid_tasks}",
        ) from None

    try:
        result = await _dispatcher.dispatch(task, req.payload, prefer_local=req.prefer_local)
        return {"source": result.source, "data": result.data, "metadata": result.metadata}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Dispatch failed")
        raise HTTPException(status_code=500, detail="Dispatch failed") from exc


@router.get("/status")
async def dispatch_status() -> dict[str, Any]:
    return _dispatcher.status()
