"""Classification candidate approval queue."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_token
from db import get_conn
from models.items import OkResult

router = APIRouter(prefix="/api/candidates", tags=["candidates"], dependencies=[Depends(require_token)])


class MergeRequest(BaseModel):
    target_name: str


@router.get("")
async def list_candidates(min_count: int = 5):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, candidate_type, name, domain, main_topic, status, target_name,
                      occurrence_count, content_count, source_counts, examples, created_at, updated_at
               FROM core.classification_candidates
               WHERE status='pending' AND occurrence_count >= %s
               ORDER BY occurrence_count DESC, updated_at DESC""",
            (min_count,),
        ).fetchall()
    return rows


def _set_status(candidate_id: int, status: str, target_name: str | None = None):
    with get_conn() as conn:
        row = conn.execute(
            """UPDATE core.classification_candidates
               SET status=%s, target_name=%s, updated_at=now()
               WHERE id=%s RETURNING id""",
            (status, target_name, candidate_id),
        ).fetchone()
        conn.commit()
    if not row:
        raise HTTPException(404, "candidate not found")


@router.post("/{candidate_id}/approve", response_model=OkResult)
async def approve(candidate_id: int):
    _set_status(candidate_id, "active")
    return OkResult()


@router.post("/{candidate_id}/merge", response_model=OkResult)
async def merge(candidate_id: int, payload: MergeRequest):
    if not payload.target_name.strip():
        raise HTTPException(400, "target_name required")
    _set_status(candidate_id, "merged", payload.target_name.strip())
    return OkResult()


@router.post("/{candidate_id}/ignore", response_model=OkResult)
async def ignore(candidate_id: int):
    _set_status(candidate_id, "ignored")
    return OkResult()
