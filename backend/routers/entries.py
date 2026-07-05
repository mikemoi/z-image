"""文字入口:速记 / 日志 / 计划 / AI 剪藏。全部落 core.entries,靠 kind 区分。

设计:捕捉零摩擦(写完就走,状态 inbox);消化时再归位进精选脑(core.notes/knowledge)。
日志主轴是时间(logged_for),按天翻 + 往年今天;计划靠 pinned 常驻不沉底。
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.types.json import Jsonb

from auth import require_token
from db import get_conn
from models.entries import (
    EntryCreate, EntryUpdate, Entry, FileEntry, FileResult, KINDS,
    validate_topic_tree_values,
)
from models.items import OkResult
from classification_schema import normalize_entry_type, normalize_source

router = APIRouter(prefix="/api/entries", tags=["entries"], dependencies=[Depends(require_token)])
MADRID = ZoneInfo("Europe/Madrid")


def _chunk(text: str, max_len: int = 1200) -> list[str]:
    """与 items 一致的初版切块:按空行分段,过长再按句号软切。"""
    paras = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
    chunks: list[str] = []
    for p in paras:
        if len(p) <= max_len:
            chunks.append(p)
            continue
        buf = ""
        for sentence in p.replace("。", "。\x00").split("\x00"):
            if len(buf) + len(sentence) > max_len and buf:
                chunks.append(buf.strip()); buf = sentence
            else:
                buf += sentence
        if buf.strip():
            chunks.append(buf.strip())
    return chunks


def _entry(row) -> Entry:
    data = dict(row)
    data["source"] = normalize_source(data.get("source"), "我")
    data["entry_type"] = normalize_entry_type(data.get("entry_type"))
    return Entry(**data)


@router.post("", response_model=Entry)
async def create_entry(payload: EntryCreate):
    """记一条(想法/日志/计划)。全部直接入流,无"待整理";想法可带来源截图。"""
    kind = payload.kind if payload.kind in KINDS else "idea"
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(400, "body 不能为空")

    logged_for = payload.logged_for
    if kind == "log" and logged_for is None:
        logged_for = datetime.now(MADRID).date()
    pinned = payload.pinned or (kind == "plan")
    source = "我"
    entry_type = payload.entry_type
    if entry_type is None and kind == "idea":
        entry_type = "想法"
    if entry_type is None and kind == "log":
        entry_type = "记录"
    with get_conn() as conn:
        row = conn.execute(
            """INSERT INTO core.entries
                      (kind, body, status, mood, pinned, logged_for, source_item_id,
                       entry_type, domain, main_topic, sub_topic, related_topics, tags,
                       use_tag, source, topics, highlights)
               VALUES (%s, %s, 'filed', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id, kind, body, status, mood, pinned, logged_for, source_item_id,
                         theme, promoted_at, entry_type, domain, main_topic, sub_topic, related_topics, tags,
                         use_tag, source, topics, highlights,
                         ai_classify_status, ai_classified_at, ai_classify_output,
                         created_at, updated_at""",
            (kind, body, payload.mood, pinned, logged_for, payload.source_item_id,
             entry_type, payload.domain, payload.main_topic, payload.sub_topic,
             Jsonb(payload.related_topics) if payload.related_topics is not None else None,
             Jsonb(payload.tags) if payload.tags is not None else None,
             payload.use_tag, source,
             Jsonb(payload.topics) if payload.topics is not None else None,
             Jsonb(payload.highlights) if payload.highlights is not None else None),
        ).fetchone()
        conn.commit()
    return _entry(row)


@router.get("/ideas", response_model=list[Entry])
async def ideas():
    """想法流:汇聚所有想法,带来源截图缩略(凭空记的没有)。你的"思维镜子"。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT e.id, e.kind, e.body, e.status, e.mood, e.pinned, e.logged_for,
                      e.source_item_id, e.theme, e.promoted_at,
                      e.entry_type, e.domain, e.main_topic, e.sub_topic, e.related_topics, e.tags,
                      e.use_tag, e.source, e.topics, e.highlights,
                      e.ai_classify_status, e.ai_classified_at, e.ai_classify_output,
                      f.checksum,
                      e.created_at, e.updated_at
               FROM core.entries e
               LEFT JOIN image.items i ON i.id = e.source_item_id
               LEFT JOIN image.files f ON f.id = i.file_id
               WHERE e.deleted_at IS NULL AND e.kind = 'idea'
               ORDER BY e.created_at DESC""",
        ).fetchall()
    return [_entry(r) for r in rows]


@router.post("/{entry_id}/promote", response_model=OkResult)
async def promote_idea(entry_id: int):
    """精选想法入脑:body 存进 core.knowledge(挂主题标签),标记 promoted_at。"""
    with get_conn() as conn:
        e = conn.execute(
            "SELECT id, body, theme, promoted_at FROM core.entries WHERE id = %s AND deleted_at IS NULL",
            (entry_id,),
        ).fetchone()
        if not e:
            raise HTTPException(404, "idea not found")
        if e["promoted_at"]:
            raise HTTPException(409, "已精选,勿重复")
        source_id = conn.execute(
            """INSERT INTO core.sources (origin_schema, origin_table, origin_id)
               VALUES ('core', 'entries', %s) RETURNING id""",
            (entry_id,),
        ).fetchone()["id"]
        kid = conn.execute(
            "INSERT INTO core.knowledge (source_id, body) VALUES (%s, %s) RETURNING id",
            (source_id, e["body"]),
        ).fetchone()["id"]
        if e["theme"]:
            tag = conn.execute(
                "SELECT id FROM core.tags WHERE name = %s AND kind = 'theme'", (e["theme"],)
            ).fetchone()
            if tag:
                conn.execute(
                    "INSERT INTO core.knowledge_tags (knowledge_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (kid, tag["id"]),
                )
        conn.execute(
            "UPDATE core.entries SET promoted_at = now(), updated_at = now() WHERE id = %s",
            (entry_id,),
        )
        conn.commit()
    return OkResult()


@router.post("/{entry_id}/reclassify", response_model=OkResult)
async def reclassify(entry_id: int):
    """重新分类:只清新分类字段；旧 use_tag/topics 保留兼容。"""
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE core.entries
               SET entry_type=NULL, domain=NULL, main_topic=NULL, sub_topic=NULL,
                   related_topics=NULL, tags=NULL,
                   ai_classify_status='pending', ai_classified_at=NULL,
                   ai_classify_output=NULL, updated_at=now()
               WHERE id=%s AND deleted_at IS NULL RETURNING id""",
            (entry_id,),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "entry not found")
    return OkResult()


@router.get("", response_model=list[Entry])
async def list_entries(
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    where = ["deleted_at IS NULL"]
    params: list = []
    if kind:
        where.append("kind = %s"); params.append(kind)
    if status:
        where.append("status = %s"); params.append(status)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT id, kind, body, status, mood, pinned, logged_for, source_item_id,
                       theme, promoted_at, entry_type, domain, main_topic, sub_topic, related_topics, tags,
                       use_tag, source, topics, highlights,
                       ai_classify_status, ai_classified_at, ai_classify_output,
                       created_at, updated_at
                FROM core.entries WHERE {" AND ".join(where)}
                ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            params + [limit, offset],
        ).fetchall()
    return [_entry(r) for r in rows]


@router.get("/inbox", response_model=list[Entry])
async def inbox():
    """待整理:速记/剪藏里还没归位的。消化节奏,无计数、无催促。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, source_item_id,
                      theme, promoted_at, entry_type, domain, main_topic, sub_topic, related_topics, tags,
                      use_tag, source, topics, highlights,
                      ai_classify_status, ai_classified_at, ai_classify_output,
                      created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND status = 'inbox'
               ORDER BY created_at DESC""",
        ).fetchall()
    return [_entry(r) for r in rows]


@router.get("/plans", response_model=list[Entry])
async def plans():
    """钉住的计划(五年/十年计划等),常驻不沉底。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, source_item_id,
                      theme, promoted_at, entry_type, domain, main_topic, sub_topic, related_topics, tags,
                      use_tag, source, topics, highlights,
                      ai_classify_status, ai_classified_at, ai_classify_output,
                      created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND kind = 'plan' AND pinned = true
               ORDER BY created_at DESC""",
        ).fetchall()
    return [_entry(r) for r in rows]


@router.get("/logs", response_model=list[Entry])
async def logs(limit: int = Query(default=200, le=500), offset: int = Query(default=0, ge=0)):
    """日志时间线:按事情发生的日期倒序。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, source_item_id,
                      theme, promoted_at, entry_type, domain, main_topic, sub_topic, related_topics, tags,
                      use_tag, source, topics, highlights,
                      ai_classify_status, ai_classified_at, ai_classify_output,
                      created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND kind = 'log'
               ORDER BY logged_for DESC NULLS LAST, created_at DESC
               LIMIT %s OFFSET %s""",
            (limit, offset),
        ).fetchall()
    return [_entry(r) for r in rows]


@router.get("/logs/on-this-day", response_model=list[Entry])
async def on_this_day():
    """往年今天:同月同日、往年的日志。温柔冒出,不催办(偶遇气质,同"重新遇见")。"""
    today = date.today()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, source_item_id,
                      theme, promoted_at, entry_type, domain, main_topic, sub_topic, related_topics, tags,
                      use_tag, source, topics, highlights,
                      ai_classify_status, ai_classified_at, ai_classify_output,
                      created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND kind = 'log' AND logged_for IS NOT NULL
                 AND EXTRACT(MONTH FROM logged_for) = %s
                 AND EXTRACT(DAY   FROM logged_for) = %s
                 AND logged_for < %s
               ORDER BY logged_for DESC""",
            (today.month, today.day, today.replace(month=1, day=1)),
        ).fetchall()
    return [_entry(r) for r in rows]


@router.get("/timeline", response_model=list[Entry])
async def timeline(day: date | None = Query(default=None, alias="date")):
    """某一天的记录时间线。默认 Europe/Madrid 今天，按创建时间正序。"""
    target = day or datetime.now(MADRID).date()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, source_item_id,
                      theme, promoted_at, entry_type, domain, main_topic, sub_topic,
                      related_topics, tags, use_tag, source, topics, highlights,
                      ai_classify_status, ai_classified_at, ai_classify_output,
                      created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND kind = 'log'
                 AND COALESCE(source, '我') IN ('我', '自己')
                 AND logged_for = %s
               ORDER BY created_at ASC""",
            (target,),
        ).fetchall()
    return [_entry(r) for r in rows]


@router.patch("/{entry_id}", response_model=Entry)
async def update_entry(entry_id: int, patch: EntryUpdate):
    fields = {k: v for k, v in patch.model_dump(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(400, "no fields to update")
    if "entry_type" in fields:
        fields["entry_type"] = normalize_entry_type(fields["entry_type"])
    if "source" in fields:
        fields["source"] = normalize_source(fields["source"])
    if fields.keys() & {"domain", "main_topic", "sub_topic", "related_topics"}:
        with get_conn() as conn:
            current = conn.execute(
                """SELECT domain, main_topic, sub_topic, related_topics FROM core.entries
                   WHERE id = %s AND deleted_at IS NULL""",
                (entry_id,),
            ).fetchone()
        if not current:
            raise HTTPException(404, "entry not found")
        try:
            validate_topic_tree_values(
                fields.get("domain", current["domain"]),
                fields.get("main_topic", current["main_topic"]),
                fields.get("sub_topic", current["sub_topic"]),
                fields.get("related_topics", current["related_topics"]),
            )
        except ValueError as e:
            raise HTTPException(422, str(e))
    for name in ("related_topics", "tags", "topics"):
        if name in fields and fields[name] is not None:
            fields[name] = Jsonb(fields[name])
    if "highlights" in fields and fields["highlights"] is not None:
        fields["highlights"] = Jsonb(fields["highlights"])
    # 人工改了任一分类维度 → 标 done,自动分类 worker 不再覆盖(人工修正优先)
    if fields.keys() & {"entry_type", "domain", "main_topic", "sub_topic", "related_topics", "tags"}:
        fields.setdefault("ai_classify_status", "done")
    sets = ", ".join(f"{k} = %s" for k in fields)
    with get_conn() as conn:
        row = conn.execute(
            f"""UPDATE core.entries SET {sets}, updated_at = now()
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id, kind, body, status, mood, pinned, logged_for,
                          source_item_id, theme, promoted_at, entry_type, domain,
                          main_topic, sub_topic, related_topics, tags, use_tag,
                          source, topics, highlights, ai_classify_status, ai_classified_at,
                          ai_classify_output, created_at, updated_at""",
            list(fields.values()) + [entry_id],
        ).fetchone()
        conn.commit()
    if not row:
        raise HTTPException(404, "entry not found")
    return _entry(row)


@router.post("/{entry_id}/file", response_model=FileResult)
async def file_entry(entry_id: int, body: FileEntry):
    """归位:把 inbox 的文字沉进精选脑。target=note→core.notes(轻);knowledge→core.knowledge(切块)。
    建 core.sources 指向本 entry(来源可追溯),原 entry 标 filed。"""
    with get_conn() as conn:
        e = conn.execute(
            "SELECT id, body FROM core.entries WHERE id = %s AND deleted_at IS NULL",
            (entry_id,),
        ).fetchone()
        if not e:
            raise HTTPException(404, "entry not found")

        source_id = conn.execute(
            """INSERT INTO core.sources (origin_schema, origin_table, origin_id)
               VALUES ('core', 'entries', %s) RETURNING id""",
            (entry_id,),
        ).fetchone()["id"]

        count = 1
        if body.target == "knowledge":
            bodies = _chunk(e["body"]) or [e["body"]]
            for seq, b in enumerate(bodies):
                conn.execute(
                    "INSERT INTO core.knowledge (source_id, body, seq) VALUES (%s, %s, %s)",
                    (source_id, b, seq),
                )
            count = len(bodies)
        else:
            conn.execute(
                "INSERT INTO core.notes (source_id, body) VALUES (%s, %s)",
                (source_id, e["body"]),
            )

        conn.execute(
            "UPDATE core.entries SET status = 'filed', updated_at = now() WHERE id = %s",
            (entry_id,),
        )
        conn.commit()
    return FileResult(target=body.target, count=count)


@router.delete("/{entry_id}", response_model=OkResult)
async def delete_entry(entry_id: int):
    """普通删除:移入回收站。"""
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE core.entries SET deleted_at=now(), updated_at=now()
               WHERE id=%s AND deleted_at IS NULL RETURNING id""", (entry_id,)
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "entry not found")
    return OkResult()


@router.post("/{entry_id}/restore", response_model=OkResult)
async def restore_entry(entry_id: int):
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE core.entries SET deleted_at=NULL, updated_at=now()
               WHERE id=%s AND deleted_at IS NOT NULL RETURNING id""", (entry_id,)
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "entry not found in trash")
    return OkResult()


@router.delete("/{entry_id}/purge", response_model=OkResult)
async def purge_entry(entry_id: int):
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM core.entries WHERE id=%s AND deleted_at IS NOT NULL RETURNING id",
            (entry_id,),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "entry not found in trash")
    return OkResult()
