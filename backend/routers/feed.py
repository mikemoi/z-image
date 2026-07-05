"""重新遇见:取 last_seen_at 最久/为空的 notes,返回后更新其 last_seen_at 轮换。"""
from fastapi import APIRouter, Depends, Query

from auth import require_token
from db import get_conn
from models.items import ResurfaceNote, OkResult

router = APIRouter(prefix="/api/feed", tags=["feed"], dependencies=[Depends(require_token)])


@router.get("/resurface", response_model=list[ResurfaceNote])
async def resurface(limit: int = Query(default=5, le=20)):
    """偶遇几条碎片。NULL(从没遇见)优先,其次最久没遇见的。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT n.id, n.body, n.use_tag, n.last_seen_at, f.checksum
               FROM core.notes n
               LEFT JOIN core.sources s ON s.id = n.source_id
               LEFT JOIN image.files f
                      ON f.id = s.origin_id AND s.origin_schema = 'image' AND s.origin_table = 'files'
               WHERE n.deleted_at IS NULL
               ORDER BY n.last_seen_at ASC NULLS FIRST
               LIMIT %s""",
            (limit,),
        ).fetchall()
        if rows:
            ids = [r["id"] for r in rows]
            conn.execute(
                "UPDATE core.notes SET last_seen_at = now() WHERE id = ANY(%s)", (ids,)
            )
            conn.commit()

    return [ResurfaceNote(**r) for r in rows]


@router.patch("/notes/{note_id}/soft-delete", response_model=OkResult)
async def delete_note(note_id: int):
    """移入回收站。"""
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE core.notes SET deleted_at=now()
               WHERE id=%s AND deleted_at IS NULL RETURNING id""", (note_id,)
        ).fetchone()
        conn.commit()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(404, "note not found")
    return OkResult()


@router.post("/notes/{note_id}/restore", response_model=OkResult)
async def restore_note(note_id: int):
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE core.notes SET deleted_at=NULL
               WHERE id=%s AND deleted_at IS NOT NULL RETURNING id""", (note_id,)
        ).fetchone()
        conn.commit()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(404, "note not found in trash")
    return OkResult()


@router.delete("/notes/{note_id}/purge", response_model=OkResult)
async def purge_note(note_id: int):
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM core.notes WHERE id=%s AND deleted_at IS NOT NULL RETURNING id",
            (note_id,),
        ).fetchone()
        conn.commit()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(404, "note not found in trash")
    return OkResult()
