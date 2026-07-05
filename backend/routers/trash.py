"""统一回收站只读聚合。恢复与永久删除复用各资源自己的端点。"""
from fastapi import APIRouter, Depends

from auth import require_token
from db import get_conn
from models.items import TrashItem

router = APIRouter(prefix="/api/trash", tags=["trash"], dependencies=[Depends(require_token)])


@router.get("", response_model=list[TrashItem])
async def list_trash():
    with get_conn() as conn:
        items = conn.execute(
            """SELECT 'item' AS kind, i.id, i.title, i.summary AS body,
                      f.checksum, i.deleted_at
               FROM image.items i JOIN image.files f ON f.id=i.file_id
               WHERE i.deleted_at IS NOT NULL"""
        ).fetchall()
        entries = conn.execute(
            """SELECT 'entry' AS kind, id, NULL AS title, body,
                      NULL AS checksum, deleted_at
               FROM core.entries WHERE deleted_at IS NOT NULL"""
        ).fetchall()
        notes = conn.execute(
            """SELECT 'note' AS kind, id, NULL AS title, body,
                      NULL AS checksum, deleted_at
               FROM core.notes WHERE deleted_at IS NOT NULL"""
        ).fetchall()
    rows = [*items, *entries, *notes]
    rows.sort(key=lambda r: r["deleted_at"], reverse=True)
    return [TrashItem(**r) for r in rows]
