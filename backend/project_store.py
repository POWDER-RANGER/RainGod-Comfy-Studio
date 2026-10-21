"""Local SQLite persistence for project generation records.

SQLite is for local development only. Shared deployment requires managed
PostgreSQL and private object storage before the service is exposed to users.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _database_path() -> Path:
    return Path(os.environ.get("RAINGOD_DB_PATH", ".raingod/raingod.sqlite3"))


def _asset_root() -> Path:
    return Path(os.environ.get("RAINGOD_ASSET_DIR", ".raingod/assets"))


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS generation_jobs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            provider_job_id TEXT,
            status TEXT NOT NULL,
            request_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            approval_json TEXT NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_generation_jobs_project_created
            ON generation_jobs(project_id, created_at);
        CREATE TABLE IF NOT EXISTS project_assets (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            job_id TEXT NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
            source_filename TEXT NOT NULL,
            storage_key TEXT NOT NULL UNIQUE,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(job_id, sha256)
        );
        CREATE INDEX IF NOT EXISTS ix_project_assets_project_created
            ON project_assets(project_id, created_at);
        """
    )
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_project(name: str, description: str = "") -> dict[str, Any]:
    project = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "created_at": _now(),
    }
    with _connect() as connection:
        connection.execute(
            "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (project["id"], name, description, project["created_at"]),
        )
    return project


def get_project(project_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, name, description, created_at FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    return dict(row) if row else None


def list_project_jobs(project_id: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """SELECT id, project_id, provider, provider_job_id, status,
                      request_json, provenance_json, approval_json, error,
                      created_at, updated_at
               FROM generation_jobs WHERE project_id = ? ORDER BY created_at""",
            (project_id,),
        ).fetchall()
    jobs: list[dict[str, Any]] = []
    for row in rows:
        job = dict(row)
        for source, target in (
            ("request_json", "request"),
            ("provenance_json", "provenance"),
            ("approval_json", "approval"),
        ):
            job[target] = json.loads(job.pop(source))
        jobs.append(job)
    return jobs


def create_generation_job(
    *,
    project_id: str,
    job_id: str,
    request: dict[str, Any],
    provenance: dict[str, Any],
    approval: dict[str, Any],
) -> None:
    timestamp = _now()
    with _connect() as connection:
        connection.execute(
            """INSERT INTO generation_jobs
               (id, project_id, provider, status, request_json, provenance_json,
                approval_json, created_at, updated_at)
               VALUES (?, ?, 'comfyui', 'submitting', ?, ?, ?, ?, ?)""",
            (
                job_id,
                project_id,
                json.dumps(request, sort_keys=True),
                json.dumps(provenance, sort_keys=True),
                json.dumps(approval, sort_keys=True),
                timestamp,
                timestamp,
            ),
        )


def update_generation_job(
    job_id: str, *, status: str, provider_job_id: str | None = None, error: str | None = None
) -> None:
    with _connect() as connection:
        connection.execute(
            """UPDATE generation_jobs
               SET status = ?, provider_job_id = ?, error = ?, updated_at = ?
               WHERE id = ?""",
            (status, provider_job_id, error, _now(), job_id),
        )


def update_job_status_by_provider_id(provider_job_id: str, status: str) -> None:
    with _connect() as connection:
        connection.execute(
            """UPDATE generation_jobs SET status = ?, updated_at = ?
               WHERE provider_job_id = ?""",
            (status, _now(), provider_job_id),
        )


def save_project_asset(
    provider_job_id: str, source_filename: str, mime_type: str, content: bytes
) -> dict[str, Any] | None:
    """Persist a fetched raster output when its provider job belongs to a project."""
    extensions = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    content_hash = hashlib.sha256(content).hexdigest()
    root = _asset_root().resolve()
    with _connect() as connection:
        job = connection.execute(
            "SELECT id, project_id FROM generation_jobs WHERE provider_job_id = ?",
            (provider_job_id,),
        ).fetchone()
        if job is None:
            return None

        extension = extensions.get(mime_type)
        if extension is None:
            raise ValueError(f"Unsupported project asset media type: {mime_type}")

        prior = connection.execute(
            """SELECT id, project_id, job_id, source_filename, storage_key,
                      mime_type, size_bytes, sha256, created_at
               FROM project_assets WHERE job_id = ? AND sha256 = ?""",
            (job["id"], content_hash),
        ).fetchone()
        if prior is not None:
            return dict(prior)

        asset_id = str(uuid.uuid4())
        storage_key = f"{job['project_id']}/{asset_id}.{extension}"
        destination = (root / storage_key).resolve()
        try:
            destination.relative_to(root)
        except ValueError as exc:
            raise ValueError("Resolved project asset path escaped its storage root") from exc
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, destination)
        asset = {
            "id": asset_id,
            "project_id": job["project_id"],
            "job_id": job["id"],
            "source_filename": source_filename,
            "storage_key": storage_key,
            "mime_type": mime_type,
            "size_bytes": len(content),
            "sha256": content_hash,
            "created_at": _now(),
        }
        try:
            connection.execute(
                """INSERT INTO project_assets
                   (id, project_id, job_id, source_filename, storage_key, mime_type,
                    size_bytes, sha256, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(asset.values()),
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return asset


def list_project_assets(project_id: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """SELECT id, project_id, job_id, source_filename, mime_type,
                      size_bytes, sha256, created_at
               FROM project_assets WHERE project_id = ? ORDER BY created_at""",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_project_asset(project_id: str, asset_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            """SELECT id, project_id, job_id, source_filename, storage_key,
                      mime_type, size_bytes, sha256, created_at
               FROM project_assets WHERE project_id = ? AND id = ?""",
            (project_id, asset_id),
        ).fetchone()
    if row is None:
        return None
    asset = dict(row)
    root = _asset_root().resolve()
    path = (root / asset["storage_key"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Resolved project asset path escaped its storage root") from exc
    asset["path"] = path
    return asset


def load_project_asset(
    project_id: str, asset_id: str
) -> tuple[dict[str, Any] | None, bytes | None]:
    """Load an asset and verify its persisted size and content hash."""
    asset = get_project_asset(project_id, asset_id)
    if asset is None:
        return None, None
    content = asset["path"].read_bytes()
    if (
        len(content) != asset["size_bytes"]
        or hashlib.sha256(content).hexdigest() != asset["sha256"]
    ):
        raise OSError("Stored project asset failed integrity verification")
    asset.pop("path")
    return asset, content
