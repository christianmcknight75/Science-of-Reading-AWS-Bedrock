"""Admin review queue: the license checklist as an API. Only admins; nothing is auto-approved."""

import re
import uuid
from pathlib import Path
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .auth import require_admin
from .config import Settings, get_settings
from .db import get_conn

router = APIRouter(prefix="/admin", tags=["admin"])
Conn = Annotated[psycopg.Connection[dict[str, Any]], Depends(get_conn)]
Admin = Annotated[str, Depends(require_admin)]

COLUMNS = (
    "source_id, title, authors, year, doi, eric_id, url, pdf_url, license, license_snapshot_url, "
    "attribution, source_type, topics, grades, status, license_checklist, reviewer_notes, "
    "approved_by, approved_at, version, discovered_from"
)


class Checklist(BaseModel):
    """The license checklist answers a reviewer records for one source."""

    copy_store: bool  # may we copy and store the full text?
    ai_use: bool  # may AI process it?
    excerpt_display: bool  # may we show exact passages to teachers?
    redistribution: bool  # recorded for the handoff; does not block approval
    derivatives: bool  # recorded for the handoff; does not block approval
    third_party_content_checked: bool  # figures/tables with their own copyright reviewed


class Decision(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer_notes: str = ""
    license: str | None = Field(default=None, max_length=100)
    attribution: str | None = Field(default=None, max_length=1000)
    source_type: Literal["practice_guide", "meta_analysis", "study", "foundational"] | None = None
    topics: list[str] = []
    grades: list[str] = []
    checklist: Checklist | None = None


@router.get("/sources")
def list_sources(
    _: Admin, conn: Conn, status: Literal["candidate", "approved", "rejected"] = "candidate"
) -> list[dict[str, Any]]:
    return conn.execute(
        f"SELECT {COLUMNS} FROM sources WHERE status = %s ORDER BY source_id",  # noqa: S608
        (status,),
    ).fetchall()


def _get(conn: Conn, source_id: str) -> dict[str, Any]:
    row = conn.execute(
        f"SELECT {COLUMNS} FROM sources WHERE source_id = %s",  # noqa: S608
        (source_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "source not found")
    return row


@router.get("/sources/{source_id}")
def get_source(source_id: str, _: Admin, conn: Conn) -> dict[str, Any]:
    return _get(conn, source_id)


@router.post("/sources/{source_id}/license-snapshot")
def upload_snapshot(
    source_id: str,
    _: Admin,
    conn: Conn,
    s: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
) -> dict[str, str]:
    """Archive a copy of the license page (PDF or HTML). Local disk for now; S3 in Phase 5."""
    _get(conn, source_id)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".pdf", ".html", ".htm", ".png", ".txt"}:
        raise HTTPException(400, "snapshot must be a pdf, html, png or txt file")
    data = file.file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "snapshot too large (10 MB max)")
    if not re.fullmatch(r"src_\d{4,}", source_id):
        raise HTTPException(400, "bad source id")
    dest_dir = Path(s.snapshot_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{source_id}_{uuid.uuid4().hex[:8]}{ext}"  # server-chosen name only
    dest.write_bytes(data)
    conn.execute(
        "UPDATE sources SET license_snapshot_url = %s WHERE source_id = %s", (str(dest), source_id)
    )
    return {"license_snapshot_url": str(dest)}


@router.post("/sources/{source_id}/decision")
def decide(source_id: str, body: Decision, reviewer: Admin, conn: Conn) -> dict[str, Any]:
    src = _get(conn, source_id)
    if body.decision == "reject":
        conn.execute(
            """UPDATE sources SET status='rejected', reviewer_notes=%s, approved_by=NULL,
               approved_at=NULL WHERE source_id=%s""",
            (body.reviewer_notes, source_id),
        )
        return _get(conn, source_id)

    problems = []
    c = body.checklist
    if c is None:
        problems.append("checklist is required")
    else:
        for name, label in [
            ("copy_store", "copying/storing"),
            ("ai_use", "AI use"),
            ("excerpt_display", "showing excerpts"),
            ("third_party_content_checked", "third-party content review"),
        ]:
            if not getattr(c, name):
                problems.append(f"license must allow/confirm {label}")
    if not (body.license or src["license"]):
        problems.append("license is required")
    if not (body.attribution or "").strip():
        problems.append("attribution is required")
    if not src["license_snapshot_url"]:
        problems.append("upload the license snapshot first")
    if problems:
        raise HTTPException(422, problems)
    assert c is not None  # noqa: S101 (narrowed above)
    conn.execute(
        """UPDATE sources SET status='approved', license=COALESCE(%s, license), attribution=%s,
             source_type=COALESCE(%s, source_type), topics=%s, grades=%s,
             license_checklist=%s::jsonb, reviewer_notes=%s, approved_by=%s, approved_at=now()
           WHERE source_id=%s""",
        (
            body.license,
            body.attribution,
            body.source_type,
            body.topics,
            body.grades,
            c.model_dump_json(),
            body.reviewer_notes,
            reviewer,
            source_id,
        ),
    )
    return _get(conn, source_id)
