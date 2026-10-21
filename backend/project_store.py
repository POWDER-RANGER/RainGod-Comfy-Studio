"""Local SQLite persistence for project generation records.

SQLite is for local development only. Shared deployment requires managed
PostgreSQL and private object storage before the service is exposed to users.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _database_path() -> Path:
    return Path(os.environ.get("RAINGOD_DB_PATH", ".raingod/raingod.sqlite3"))


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
