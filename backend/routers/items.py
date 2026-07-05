"""条目路由:上传、列表、详情、软删/恢复/彻底销毁。

上传关键约束:同步落库即返回,绝不在请求里等任何慢操作(AI 是第三步的后台任务)。
所有列表查询默认 WHERE deleted_at IS NULL。
"""
import os
import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from psycopg.types.json import Jsonb

from auth import require_token
from db import get_conn
from config import FILES_ROOT
from worker import process_item
from vision import call_insight
from settings_store import insight_model
from models.items import (
    UploadResult, ItemBrief, ItemDetail, ItemList, OkResult,
    ItemUpdate, DimensionStats, PromoteResult, NoteResult,
    InsightResult, AdoptTheme,
)
from models.entries import CleanupItem

router = APIRouter(prefix="/api/items", tags=["items"], dependencies=[Depends(require_token)])

IMAGE_DIR = Path(FILES_ROOT) / "image"


def _ext_from_name(name: str) -> str:
    """从原始文件名取扩展名,缺省 .jpg。只留字母数字,防注入。"""
    ext = Path(name or "").suffix.lower().lstrip(".")
    ext = "".join(c for c in ext if c.isalnum())
    return ext or "jpg"


def _chunk(text: str, max_len: int = 1200) -> list[str]:
    """初版切块:按空行分段;过长段再按句号软切。返回非空块列表。"""
    paras = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
    chunks: list[str] = []
    for p in paras:
        if len(p) <= max_len:
            chunks.append(p)
            continue
        buf = ""
        for sentence in p.replace("。", "。\x00").split("\x00"):
            if len(buf) + len(sentence) > max_len and buf:
                chunks.append(buf.strip())
                buf = sentence
            else:
                buf += sentence
        if buf.strip():
            chunks.append(buf.strip())
    return chunks


@router.post("/upload", response_model=UploadResult)
async def upload(images: list[UploadFile] = File(...)):
    """批量上传。逐张:算 sha256 → 存盘(已存在则复用)→ files/items 落库 → 立即返回。"""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    received = 0

    with get_conn() as conn:
        for up in images:
            try:
                data = await up.read()
                if not data:
                    continue
                checksum = hashlib.sha256(data).hexdigest()
                ext = _ext_from_name(up.filename)
                filename = f"{checksum}.{ext}"
                abs_path = IMAGE_DIR / filename
                # checksum 命名天然去重:同内容同文件名,已存在就不重复写盘
                if not abs_path.exists():
                    abs_path.write_bytes(data)
                # DB 里存磁盘路径(与部署环境一致的绝对/相对形式)
                file_path = str(abs_path)

                # files 行按 checksum 复用,保持文件表与磁盘 1:1;item 每次新建
                row = conn.execute(
                    "SELECT id FROM image.files WHERE checksum = %s LIMIT 1",
                    (checksum,),
                ).fetchone()
                if row:
                    file_id = row["id"]
                else:
                    file_id = conn.execute(
                        """INSERT INTO image.files
                               (file_path, file_type, original_filename, checksum, file_size)
                           VALUES (%s, 'image', %s, %s, %s)
                           RETURNING id""",
                        (file_path, up.filename or filename, checksum, len(data)),
                    ).fetchone()["id"]

                conn.execute(
                    "INSERT INTO image.items (file_id, status) VALUES (%s, 'review')",
                    (file_id,),
                )
                received += 1
            except Exception:
                # 单张失败不影响其余;不阻塞"手机可清空"的体感
                continue
        conn.commit()

    return UploadResult(received=received, message=f"已接收 {received} 张,手机可清空")


@router.post("/{item_id}/process", response_model=ItemDetail)
async def process_now(item_id: int):
    """同步跑一遍 Vision 处理(测试/调试用),完成后返回详情。"""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT i.id, f.file_path FROM image.items i
               JOIN image.files f ON f.id = i.file_id
               WHERE i.id = %s AND i.deleted_at IS NULL""",
            (item_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "item not found")
    ok = await process_item(item_id, row["file_path"])
    if not ok:
        raise HTTPException(502, "vision processing failed, item left in review")
    return await get_item(item_id)


@router.post("/{item_id}/reprocess", response_model=OkResult)
async def reprocess(item_id: int):
    """清掉旧结果、重置为待处理,让后台 worker 再跑一次。"""
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE image.items
               SET status='review', ai_output=NULL, title=NULL, summary=NULL,
                   theme=NULL, use_tag=NULL, granularity=NULL,
                   is_ocr_suitable=false, reviewed_at=NULL, updated_at=now()
               WHERE id=%s AND deleted_at IS NULL RETURNING id""",
            (item_id,),
        ).fetchone()
        if r:
            conn.execute("DELETE FROM image.contents WHERE item_id=%s", (item_id,))
        conn.commit()
    if not r:
        raise HTTPException(404, "item not found")
    return OkResult()


# ── 「问问 AI」:按需生成看法(拉不推)+ 采纳提议的新分类(你点头才生效) ──────────
@router.post("/{item_id}/insight", response_model=InsightResult)
async def insight(item_id: int, refresh: bool = Query(default=False)):
    """详情页主动点击才调 AI(省钱),结果缓存进 ai_insight;refresh=true 强制重算。"""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT i.id, f.file_path, i.title, i.summary, i.ai_insight
               FROM image.items i
               JOIN image.files f ON f.id = i.file_id
               WHERE i.id = %s AND i.deleted_at IS NULL""",
            (item_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "item not found")
        if row["ai_insight"] and not refresh:
            return InsightResult(**row["ai_insight"], cached=True)
        content = conn.execute(
            """SELECT clean_text FROM image.contents
               WHERE item_id = %s AND is_current = true
               ORDER BY created_at DESC LIMIT 1""",
            (item_id,),
        ).fetchone()
        themes = conn.execute(
            "SELECT name FROM core.tags WHERE kind = 'theme' ORDER BY id"
        ).fetchall()

    existing = [t["name"] for t in themes]
    context = {
        "title": row["title"],
        "summary": row["summary"],
        "clean_text": content["clean_text"] if content else None,
    }
    try:
        result = await call_insight(row["file_path"], context, existing, model=insight_model())
    except Exception as e:  # noqa: BLE001 —— 外部调用失败直接告知,不缓存
        raise HTTPException(502, f"AI 调用失败: {e}")

    # 若模型提议的"新分类"其实已存在,视为无提议(护栏:优先用已有分类)
    if result["suggested_theme"] and result["suggested_theme"].lower() in {
        e.lower() for e in existing
    }:
        result["suggested_theme"] = None
        result["suggested_theme_reason"] = None

    with get_conn() as conn:
        conn.execute(
            "UPDATE image.items SET ai_insight = %s, updated_at = now() WHERE id = %s",
            (Jsonb(result), item_id),
        )
        conn.commit()
    return InsightResult(**result, cached=False)


@router.post("/{item_id}/adopt-theme", response_model=ItemDetail)
async def adopt_theme(item_id: int, body: AdoptTheme):
    """采纳 AI 提议的新分类:建 theme tag(生长)+ 打到本条上。"""
    name = (body.theme or "").strip()
    if not name:
        raise HTTPException(400, "theme required")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO core.tags (name, kind) VALUES (%s, 'theme') ON CONFLICT DO NOTHING",
            (name,),
        )
        r = conn.execute(
            """UPDATE image.items SET theme = %s, updated_at = now()
               WHERE id = %s AND deleted_at IS NULL RETURNING id""",
            (name, item_id),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "item not found")
    return await get_item(item_id)


# ── 清库仪式:列出 AI 判为『无信息量』的(主动进入才聚合,不推送、不计数) ──────────
@router.get("/cleanup", response_model=list[CleanupItem])
async def cleanup_suggestions(limit: int = Query(default=200, le=500)):
    """AI 在自动处理时顺手判的 quality='无信息量'。你想清库时才来看,一眼扫、一键删。
    红线:'鸡汤'≠该删,反面样本仍有避坑价值,这里只出纯无信息量的。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT i.id, f.checksum, i.title, i.summary,
                      i.ai_insight->>'quality_note' AS quality_note
               FROM image.items i
               JOIN image.files f ON f.id = i.file_id
               WHERE i.deleted_at IS NULL
                 AND i.ai_output->>'quality' = '无信息量'
               ORDER BY i.created_at DESC
               LIMIT %s""",
            (limit,),
        ).fetchall()
    return [CleanupItem(**r) for r in rows]


# ── 消化闭环:闸门一 review / 闸门二 入脑 / 碎片落箱 ──────────────────────────
@router.patch("/{item_id}/review", response_model=OkResult)
async def review(item_id: int):
    """闸门一:标记已看。"""
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE image.items SET reviewed_at = now(), updated_at = now()
               WHERE id = %s AND deleted_at IS NULL RETURNING id""",
            (item_id,),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "item not found")
    return OkResult()


@router.patch("/{item_id}/promote", response_model=PromoteResult)
async def promote(item_id: int):
    """闸门二(knowledge 类):切块入 core.knowledge,挂 theme/use 标签。需先 review。"""
    with get_conn() as conn:
        item = conn.execute(
            """SELECT id, file_id, title, summary, theme, use_tag, granularity,
                      reviewed_at, promoted_at
               FROM image.items WHERE id = %s AND deleted_at IS NULL""",
            (item_id,),
        ).fetchone()
        if not item:
            raise HTTPException(404, "item not found")
        if item["granularity"] == "asset":
            raise HTTPException(422, "资料类不入脑,仅存档检索")
        if item["promoted_at"]:
            raise HTTPException(409, "已精选,勿重复")

        content = conn.execute(
            """SELECT clean_text FROM image.contents
               WHERE item_id = %s AND is_current = true
               ORDER BY created_at DESC LIMIT 1""",
            (item_id,),
        ).fetchone()

        # 有正文按段落切块;无正文(图解类)用 summary 单块
        bodies = _chunk(content["clean_text"]) if content and content["clean_text"] else []
        if not bodies and item["summary"]:
            bodies = [item["summary"]]
        if not bodies:
            raise HTTPException(422, "没有可入脑的正文或摘要")

        source_id = conn.execute(
            """INSERT INTO core.sources (origin_schema, origin_table, origin_id)
               VALUES ('image', 'files', %s) RETURNING id""",
            (item["file_id"],),
        ).fetchone()["id"]

        # theme/use 标签(预置),取 id
        tag_ids: list[int] = []
        for name, kind in ((item["theme"], "theme"), (item["use_tag"], "use")):
            if not name:
                continue
            row = conn.execute(
                "SELECT id FROM core.tags WHERE name = %s AND kind = %s", (name, kind)
            ).fetchone()
            if row:
                tag_ids.append(row["id"])

        knowledge_ids: list[int] = []
        for seq, body in enumerate(bodies):
            kid = conn.execute(
                """INSERT INTO core.knowledge (source_id, title, body, seq, summary)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (source_id, item["title"], body, seq, item["summary"]),
            ).fetchone()["id"]
            knowledge_ids.append(kid)
            for tid in tag_ids:
                conn.execute(
                    """INSERT INTO core.knowledge_tags (knowledge_id, tag_id)
                       VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                    (kid, tid),
                )

        conn.execute(
            "UPDATE image.items SET promoted_at = now(), updated_at = now() WHERE id = %s",
            (item_id,),
        )
        conn.commit()

    return PromoteResult(knowledge_ids=knowledge_ids, count=len(knowledge_ids))


@router.post("/{item_id}/to-note", response_model=NoteResult)
async def to_note(item_id: int):
    """碎片落箱(fragment 类):body 取 summary 或 clean_text,无第二道闸门。"""
    with get_conn() as conn:
        item = conn.execute(
            "SELECT id, file_id, summary, use_tag, granularity FROM image.items WHERE id = %s AND deleted_at IS NULL",
            (item_id,),
        ).fetchone()
        if not item:
            raise HTTPException(404, "item not found")
        if item["granularity"] == "asset":
            raise HTTPException(422, "资料类不进收集箱,仅存档检索")

        body = item["summary"]
        if not body:
            c = conn.execute(
                """SELECT clean_text FROM image.contents
                   WHERE item_id = %s AND is_current = true
                   ORDER BY created_at DESC LIMIT 1""",
                (item_id,),
            ).fetchone()
            body = c["clean_text"] if c else None
        if not body:
            raise HTTPException(422, "没有可落箱的内容")

        source_id = conn.execute(
            """INSERT INTO core.sources (origin_schema, origin_table, origin_id)
               VALUES ('image', 'files', %s) RETURNING id""",
            (item["file_id"],),
        ).fetchone()["id"]
        note_id = conn.execute(
            """INSERT INTO core.notes (source_id, body, use_tag)
               VALUES (%s, %s, %s) RETURNING id""",
            (source_id, body, item["use_tag"]),
        ).fetchone()["id"]
        # 落箱即视为消化过,标 promoted 便于前端区分
        conn.execute(
            "UPDATE image.items SET promoted_at = now(), updated_at = now() WHERE id = %s",
            (item_id,),
        )
        conn.commit()

    return NoteResult(note_id=note_id)


def _review_filter_sql(entry_type: str | None, domain: str | None, use_tag: str | None):
    clauses: list[str] = []
    params: list[str] = []
    for column, value in (("i.entry_type", entry_type), ("i.domain", domain), ("i.use_tag", use_tag)):
        if value:
            clauses.append(f"{column}=%s")
            params.append(value)
    return clauses, params


def _reading_queue(where: str, limit: int, order: str,
                   entry_type: str | None = None, domain: str | None = None,
                   use_tag: str | None = None) -> ItemList:
    filters, params = _review_filter_sql(entry_type, domain, use_tag)
    extra = "".join(f" AND {clause}" for clause in filters)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT i.id, i.file_id, f.checksum, i.status, i.title, i.summary,
                       i.theme, i.use_tag, i.granularity, i.entry_type, i.domain,
                       i.topics, i.highlights, i.ai_classify_status,
                       i.reviewed_at, i.promoted_at, i.created_at
                FROM image.items i JOIN image.files f ON f.id=i.file_id
                WHERE i.deleted_at IS NULL AND i.status='ok' AND {where}{extra}
                ORDER BY {order} LIMIT %s""",
            [*params, limit],
        ).fetchall()
    return ItemList(total=len(rows), limit=limit, offset=0,
                    items=[ItemBrief(**r) for r in rows])


@router.get("/review-queue", response_model=ItemList)
async def review_queue(
    limit: int = Query(default=10, ge=1, le=20),
    entry_type: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    use_tag: str | None = Query(default=None),
):
    """集中批阅:只取尚未人工看过的内容,每组默认 10 条。"""
    return _reading_queue("i.reviewed_at IS NULL", limit, "i.created_at ASC",
                          entry_type, domain, use_tag)


@router.get("/review-facets")
async def review_facets():
    """集中批阅的未阅内容构成，供分类入口显示数量。"""
    with get_conn() as conn:
        total = conn.execute(
            """SELECT count(*) AS c FROM image.items i
               WHERE i.deleted_at IS NULL AND i.status='ok' AND i.reviewed_at IS NULL"""
        ).fetchone()["c"]
        result = {}
        for key, column in (("entry_types", "entry_type"), ("domains", "domain"), ("uses", "use_tag")):
            rows = conn.execute(
                f"""SELECT i.{column} AS value, count(*) AS c FROM image.items i
                    WHERE i.deleted_at IS NULL AND i.status='ok' AND i.reviewed_at IS NULL
                      AND i.{column} IS NOT NULL
                    GROUP BY i.{column}"""
            ).fetchall()
            result[key] = {row["value"]: row["c"] for row in rows}
    return {"total": total, **result}


@router.get("/recommendations", response_model=ItemList)
async def recommendations(limit: int = Query(default=10, ge=1, le=20)):
    """今日推荐:优先最久没看/从未看过的内容。"""
    return _reading_queue("true", limit, "i.reviewed_at ASC NULLS FIRST, i.created_at ASC")


@router.get("", response_model=ItemList)
async def list_items(
    status: str | None = Query(default=None),
    theme: str | None = Query(default=None),
    use: str | None = Query(default=None),
    granularity: str | None = Query(default=None),
    deleted: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """列表筛选。deleted=false 只看正常项;deleted=true 看回收站。"""
    where = ["i.deleted_at IS NOT NULL"] if deleted else ["i.deleted_at IS NULL"]
    params: list = []
    for col, val in (("i.status", status), ("i.theme", theme),
                     ("i.use_tag", use), ("i.granularity", granularity)):
        if val is not None:
            where.append(f"{col} = %s")
            params.append(val)
    where_sql = " AND ".join(where)

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT count(*) AS c FROM image.items i WHERE {where_sql}", params
        ).fetchone()["c"]
        rows = conn.execute(
            f"""SELECT i.id, i.file_id, f.checksum, i.status, i.title, i.summary,
                       i.theme, i.use_tag, i.granularity,
                       i.entry_type, i.domain, i.topics, i.highlights, i.ai_classify_status,
                       i.reviewed_at, i.promoted_at, i.created_at
                FROM image.items i
                JOIN image.files f ON f.id = i.file_id
                WHERE {where_sql}
                ORDER BY i.created_at DESC
                LIMIT %s OFFSET %s""",
            params + [limit, offset],
        ).fetchall()

    return ItemList(
        total=total, limit=limit, offset=offset,
        items=[ItemBrief(**r) for r in rows],
    )


@router.get("/{item_id}", response_model=ItemDetail)
async def get_item(item_id: int):
    """详情:含原图 checksum + 当前正文(clean_text/raw_text)。"""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT i.id, i.file_id, f.checksum, f.original_filename, i.status,
                      i.title, i.summary, i.theme, i.use_tag, i.granularity,
                      i.entry_type, i.domain, i.topics, i.highlights, i.ai_classify_status,
                      i.is_ocr_suitable, i.reviewed_at, i.promoted_at, i.created_at
               FROM image.items i
               JOIN image.files f ON f.id = i.file_id
               WHERE i.id = %s AND i.deleted_at IS NULL""",
            (item_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "item not found")
        content = conn.execute(
            """SELECT clean_text, raw_text FROM image.contents
               WHERE item_id = %s AND is_current = true
               ORDER BY created_at DESC LIMIT 1""",
            (item_id,),
        ).fetchone()

    return ItemDetail(
        **row,
        clean_text=content["clean_text"] if content else None,
        raw_text=content["raw_text"] if content else None,
    )


_UPDATABLE = {"title", "theme", "use_tag", "status", "granularity",
              "entry_type", "domain", "topics", "highlights"}


@router.patch("/{item_id}", response_model=ItemDetail)
async def update_item(item_id: int, patch: ItemUpdate):
    """改标签:更新可编辑字段(含 5 维分类)。人工改分类维度则不再被自动分类覆盖。"""
    fields = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if k in _UPDATABLE}
    if not fields:
        raise HTTPException(400, "no updatable fields provided")
    if "topics" in fields:
        fields["topics"] = Jsonb(fields["topics"]) if fields["topics"] is not None else None
    if "highlights" in fields:
        fields["highlights"] = Jsonb(fields["highlights"]) if fields["highlights"] is not None else None
    if fields.keys() & {"entry_type", "domain", "topics"}:
        fields.setdefault("ai_classify_status", "done")
    sets = ", ".join(f"{k} = %s" for k in fields)
    params = list(fields.values()) + [item_id]
    with get_conn() as conn:
        r = conn.execute(
            f"""UPDATE image.items SET {sets}, updated_at = now()
                WHERE id = %s AND deleted_at IS NULL RETURNING id""",
            params,
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "item not found")
    return await get_item(item_id)


@router.patch("/{item_id}/soft-delete", response_model=OkResult)
async def soft_delete(item_id: int):
    """一键软删:置 deleted_at,从所有列表消失,原文件与记录仍在。"""
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE image.items SET deleted_at = now(), updated_at = now()
               WHERE id = %s AND deleted_at IS NULL RETURNING id""",
            (item_id,),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "item not found or already deleted")
    return OkResult()


@router.post("/{item_id}/restore", response_model=OkResult)
async def restore(item_id: int):
    """从回收站恢复。"""
    with get_conn() as conn:
        r = conn.execute(
            """UPDATE image.items SET deleted_at = NULL, updated_at = now()
               WHERE id = %s AND deleted_at IS NOT NULL RETURNING id""",
            (item_id,),
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(404, "item not found in trash")
    return OkResult()


@router.delete("/{item_id}/purge", response_model=OkResult)
async def purge(item_id: int):
    """彻底销毁:删记录 + 抹磁盘原文件(仅当无其他 item 再引用该文件)。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT file_id FROM image.items WHERE id = %s AND deleted_at IS NOT NULL", (item_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "item not found in trash")
        file_id = row["file_id"]

        conn.execute("DELETE FROM image.items WHERE id = %s", (item_id,))

        # 该文件是否还有别的 item 引用;没有才删文件行+磁盘
        still = conn.execute(
            "SELECT 1 FROM image.items WHERE file_id = %s LIMIT 1", (file_id,)
        ).fetchone()
        if not still:
            frow = conn.execute(
                "SELECT file_path FROM image.files WHERE id = %s", (file_id,)
            ).fetchone()
            conn.execute("DELETE FROM image.files WHERE id = %s", (file_id,))
            if frow:
                try:
                    os.remove(frow["file_path"])
                except OSError:
                    pass  # 文件已不在则忽略
        conn.commit()
    return OkResult()
