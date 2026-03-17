"""Dispatch endpoints — /dispatch and /dispatch/status."""

from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .dispatcher import RainGodDispatcher, TaskType

router = APIRouter(prefix="/dispatch", tags=["dispatch"])
_dispatcher = RainGodDispatcher()


class DispatchRequest(BaseModel):
    task_type: str
    payload: dict[str, Any] = {}
    prefer_local: bool = True


@router.post("")
async def dispatch(req: DispatchRequest):
    try:
        task = TaskType(req.task_type)
    except ValueError:
        raise HTTPException(400, f"Unknown task_type: {req.task_type}. Valid: {[t.value for t in TaskType]}")
    try:
        result = await _dispatcher.dispatch(task, req.payload, prefer_local=req.prefer_local)
        return {"source": result.source, "data": result.data, "metadata": result.metadata}
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, f"Dispatch failed: {e}")


@router.get("/status")
async def dispatch_status():
    return _dispatcher.status()
