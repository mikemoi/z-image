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


def _jsonb_tag(tag: str) -> str:
    return f'["{tag}"]'


def _append_tag_sql(table: str, tag: str) -> str:
    return (
        f"tags = CASE WHEN COALESCE(tags, '[]'::jsonb) @> '{_jsonb_tag(tag)}'::jsonb "
        f"THEN COALESCE(tags, '[]'::jsonb) ELSE COALESCE(tags, '[]'::jsonb) || '{_jsonb_tag(tag)}'::jsonb END"
    )


def _apply_subtopic_migrations(conn, table: str):
    updates = [
        ("生活", "日常", "洗澡", "生活", "日常", "清洁", "洗澡", None),
        ("生活", "居住", "住家证明", "生活", "证件", "住家证明", None, None),
        ("能力", "编程", "Docker", "能力", "服务器", "Docker", "Dockerfile", "编程"),
        ("能力", "编程", "部署", "能力", "服务器", "部署", None, "编程"),
        ("能力", "产品", "第二脑", "能力", "产品", "ZBrain", "第二脑", None),
        ("能力", "产品", "分类系统", "能力", "产品", "内容坐标", "分类系统", None),
        ("财务", "债务", "风险", "财务", "债务", "债务风险", None, None),
        ("财务", "投资", "风险", "财务", "投资", "投资风险", None, None),
    ]
    for old_domain, old_topic, old_sub, new_domain, new_topic, new_sub, tag, related in updates:
        sets = ["domain=%s", "main_topic=%s", "sub_topic=%s"]
        params = [new_domain, new_topic, new_sub]
        if tag:
            sets.append(_append_tag_sql(table, tag))
        if related:
            sets.append(
                """related_topics = CASE
                     WHEN COALESCE(related_topics, '[]'::jsonb) @> %s::jsonb
                     THEN COALESCE(related_topics, '[]'::jsonb)
                     ELSE COALESCE(related_topics, '[]'::jsonb) || %s::jsonb END"""
            )
            params.extend([_jsonb_tag(related), _jsonb_tag(related)])
        params.extend([old_domain, old_topic, old_sub])
        conn.execute(
            f"""UPDATE {table}
                SET {", ".join(sets)}, updated_at=now()
                WHERE domain=%s AND main_topic=%s AND sub_topic=%s""",
            params,
        )


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
        _apply_subtopic_migrations(conn, "core.entries")
        _apply_subtopic_migrations(conn, "image.items")
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
