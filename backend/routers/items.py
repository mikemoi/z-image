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
from models.items import (
    UploadResult, ItemBrief, ItemDetail, ItemList, OkResult,
)

router = APIRouter(prefix="/api/items", tags=["items"], dependencies=[Depends(require_token)])

IMAGE_DIR = Path(FILES_ROOT) / "image"


def _ext_from_name(name: str) -> str:
    """从原始文件名取扩展名,缺省 .jpg。只留字母数字,防注入。"""
    ext = Path(name or "").suffix.lower().lstrip(".")
    ext = "".join(c for c in ext if c.isalnum())
    return ext or "jpg"


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
            "SELECT file_id FROM image.items WHERE id = %s", (item_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "item not found")
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
