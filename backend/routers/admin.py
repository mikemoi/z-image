"""Admin maintenance endpoints for classification re-queueing."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_token
from db import get_conn

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_token)])


class ReclassifyRequest(BaseModel):
    scope: Literal["all", "mine", "external", "unclassified", "entries", "items"] = "all"
    mode: Literal["fill_missing", "force"] = "fill_missing"


def _source_clause(alias: str, scope: str) -> str:
    source = f"COALESCE({alias}.source, '')"
    if scope == "mine":
        return f" AND {source} IN ('我', '自己')"
    if scope == "external":
        return f" AND {source} IN ('图片', '截图', '文件')"
    return ""


@router.post("/reclassify")
async def reclassify_all(payload: ReclassifyRequest):
    """Queue existing content for background classification. Never calls AI inline."""
    if payload.scope not in {"all", "mine", "external", "unclassified", "entries", "items"}:
        raise HTTPException(400, "invalid scope")
    with get_conn() as conn:
        # Deterministic compatibility fixes first.
        conn.execute("UPDATE core.entries SET source='我' WHERE source='自己'")
        conn.execute("UPDATE core.entries SET source='图片' WHERE source='截图'")
        conn.execute("UPDATE image.items SET source='图片' WHERE source='截图' OR source IS NULL")
        conn.execute("UPDATE core.entries SET entry_type='想法' WHERE entry_type='句子'")
        conn.execute("UPDATE core.entries SET entry_type='规则' WHERE entry_type='决策'")
        conn.execute("UPDATE image.items SET entry_type='想法' WHERE entry_type='句子'")
        conn.execute("UPDATE image.items SET entry_type='规则' WHERE entry_type='决策'")
        conn.execute(
            "UPDATE core.entries SET sub_topic='未细分' WHERE main_topic IS NOT NULL AND sub_topic IS NULL"
        )
        conn.execute(
            "UPDATE image.items SET sub_topic='未细分' WHERE main_topic IS NOT NULL AND sub_topic IS NULL"
        )

        queued_entries = 0
        queued_items = 0
        if payload.scope not in {"items"}:
            where = "deleted_at IS NULL" + _source_clause("core.entries", payload.scope)
            if payload.scope == "unclassified" or payload.mode == "fill_missing":
                where += """ AND (entry_type IS NULL OR domain IS NULL OR main_topic IS NULL
                              OR sub_topic IS NULL)"""
            if payload.mode == "force":
                row = conn.execute(
                    f"""UPDATE core.entries
                        SET entry_type=NULL, domain=NULL, main_topic=NULL, sub_topic=NULL,
                            related_topics=NULL, tags=NULL,
                            ai_classify_status='pending', ai_classified_at=NULL,
                            ai_classify_output=NULL, updated_at=now()
                        WHERE {where}
                        RETURNING id"""
                ).fetchall()
            else:
                row = conn.execute(
                    f"""UPDATE core.entries
                        SET ai_classify_status='pending', ai_classified_at=NULL, updated_at=now()
                        WHERE {where}
                        RETURNING id"""
                ).fetchall()
            queued_entries = len(row)

        if payload.scope not in {"entries", "mine"}:
            where = "deleted_at IS NULL AND status='ok'" + _source_clause("image.items", payload.scope)
            if payload.scope == "unclassified" or payload.mode == "fill_missing":
                where += """ AND (entry_type IS NULL OR domain IS NULL OR main_topic IS NULL
                              OR sub_topic IS NULL)"""
            if payload.mode == "force":
                row = conn.execute(
                    f"""UPDATE image.items
                        SET entry_type=NULL, domain=NULL, main_topic=NULL, sub_topic=NULL,
                            related_topics=NULL, tags=NULL,
                            ai_classify_status='pending', ai_classified_at=NULL, updated_at=now()
                        WHERE {where}
                        RETURNING id"""
                ).fetchall()
            else:
                row = conn.execute(
                    f"""UPDATE image.items
                        SET ai_classify_status='pending', ai_classified_at=NULL, updated_at=now()
                        WHERE {where}
                        RETURNING id"""
                ).fetchall()
            queued_items = len(row)
        conn.commit()
    return {"ok": True, "queued_entries": queued_entries, "queued_items": queued_items}
