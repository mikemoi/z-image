"""文字入口:速记 / 日志 / 计划 / AI 剪藏。全部落 core.entries,靠 kind 区分。

设计:捕捉零摩擦(写完就走,状态 inbox);消化时再归位进精选脑(core.notes/knowledge)。
日志主轴是时间(logged_for),按天翻 + 往年今天;计划靠 pinned 常驻不沉底。
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_token
from db import get_conn
from models.entries import (
    EntryCreate, EntryUpdate, Entry, FileEntry, FileResult, KINDS,
)
from models.items import OkResult

router = APIRouter(prefix="/api/entries", tags=["entries"], dependencies=[Depends(require_token)])


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


@router.post("", response_model=Entry)
async def create_entry(payload: EntryCreate):
    """记一条(想法/日志/计划)。全部直接入流,无"待整理";想法可带来源截图。"""
    kind = payload.kind if payload.kind in KINDS else "idea"
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(400, "body 不能为空")

    logged_for = payload.logged_for
    if kind == "log" and logged_for is None:
        logged_for = date.today()
    pinned = payload.pinned or (kind == "plan")
    with get_conn() as conn:
        row = conn.execute(
            """INSERT INTO core.entries (kind, body, status, mood, pinned, logged_for, source_item_id)
               VALUES (%s, %s, 'filed', %s, %s, %s, %s)
               RETURNING id, kind, body, status, mood, pinned, logged_for, source_item_id,
                         created_at, updated_at""",
            (kind, body, payload.mood, pinned, logged_for, payload.source_item_id),
        ).fetchone()
        conn.commit()
    return Entry(**row)


@router.get("/ideas", response_model=list[Entry])
async def ideas():
    """想法流:汇聚所有想法,带来源截图缩略(凭空记的没有)。你的"思维镜子"。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT e.id, e.kind, e.body, e.status, e.mood, e.pinned, e.logged_for,
                      e.source_item_id, f.checksum, e.created_at, e.updated_at
               FROM core.entries e
               LEFT JOIN image.items i ON i.id = e.source_item_id
               LEFT JOIN image.files f ON f.id = i.file_id
               WHERE e.deleted_at IS NULL AND e.kind = 'idea'
               ORDER BY e.created_at DESC""",
        ).fetchall()
    return [Entry(**r) for r in rows]


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
            f"""SELECT id, kind, body, status, mood, pinned, logged_for, created_at, updated_at
                FROM core.entries WHERE {" AND ".join(where)}
                ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            params + [limit, offset],
        ).fetchall()
    return [Entry(**r) for r in rows]


@router.get("/inbox", response_model=list[Entry])
async def inbox():
    """待整理:速记/剪藏里还没归位的。消化节奏,无计数、无催促。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND status = 'inbox'
               ORDER BY created_at DESC""",
        ).fetchall()
    return [Entry(**r) for r in rows]


@router.get("/plans", response_model=list[Entry])
async def plans():
    """钉住的计划(五年/十年计划等),常驻不沉底。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND kind = 'plan' AND pinned = true
               ORDER BY created_at DESC""",
        ).fetchall()
    return [Entry(**r) for r in rows]


@router.get("/logs", response_model=list[Entry])
async def logs(limit: int = Query(default=200, le=500), offset: int = Query(default=0, ge=0)):
    """日志时间线:按事情发生的日期倒序。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND kind = 'log'
               ORDER BY logged_for DESC NULLS LAST, created_at DESC
               LIMIT %s OFFSET %s""",
            (limit, offset),
        ).fetchall()
    return [Entry(**r) for r in rows]


@router.get("/logs/on-this-day", response_model=list[Entry])
async def on_this_day():
    """往年今天:同月同日、往年的日志。温柔冒出,不催办(偶遇气质,同"重新遇见")。"""
    today = date.today()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, kind, body, status, mood, pinned, logged_for, created_at, updated_at
               FROM core.entries
               WHERE deleted_at IS NULL AND kind = 'log' AND logged_for IS NOT NULL
                 AND EXTRACT(MONTH FROM logged_for) = %s
                 AND EXTRACT(DAY   FROM logged_for) = %s
                 AND logged_for < %s
               ORDER BY logged_for DESC""",
            (today.month, today.day, today.replace(month=1, day=1)),
        ).fetchall()
    return [Entry(**r) for r in rows]


@router.patch("/{entry_id}", response_model=Entry)
async def update_entry(entry_id: int, patch: EntryUpdate):
    fields = {k: v for k, v in patch.model_dump(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(400, "no fields to update")
    sets = ", ".join(f"{k} = %s" for k in fields)
    with get_conn() as conn:
        row = conn.execute(
            f"""UPDATE core.entries SET {sets}, updated_at = now()
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id, kind, body, status, mood, pinned, logged_for, created_at, updated_at""",
            list(fields.values()) + [entry_id],
        ).fetchone()
        conn.commit()
    if not row:
        raise HTTPException(404, "entry not found")
    return Entry(**row)


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
    """永久删除(无回收站):点了就删,确定不要了才删。"""
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM core.entries WHERE id = %s RETURNING id", (entry_id,)
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "entry not found")
    return OkResult()
