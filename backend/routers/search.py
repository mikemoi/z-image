"""全文检索:覆盖全部上传条目(标题/摘要/正文),不再只搜"已入脑"的。

修复:旧版只查 core.knowledge,而用户基本不入脑 → 搜什么都空、证件永远搜不到。
现在直接搜 image.items(未删),中文无空格走 ILIKE 子串,零额外成本、几千条足够快。
"""
from fastapi import APIRouter, Depends, Query

from auth import require_token
from db import get_conn
from models.items import SearchHit

router = APIRouter(prefix="/api/search", tags=["search"], dependencies=[Depends(require_token)])


def _snippet(text: str, q: str, span: int = 40) -> str | None:
    """取正文里命中词周围一小段,方便预览。找不到则返回开头一截。"""
    if not text:
        return None
    i = text.lower().find(q.lower())
    if i == -1:
        return text[:span * 2].strip() or None
    start = max(0, i - span)
    end = min(len(text), i + len(q) + span)
    return ("…" if start > 0 else "") + text[start:end].strip() + ("…" if end < len(text) else "")


@router.get("", response_model=list[SearchHit])
async def search(q: str = Query(..., min_length=1), limit: int = Query(default=50, le=200)):
    """按关键词检索全部截图条目(标题/摘要/正文)+ 手写文字(速记/日志/计划/剪藏)。"""
    like = f"%{q}%"
    hits: list[SearchHit] = []
    with get_conn() as conn:
        img_rows = conn.execute(
            """SELECT i.id AS item_id, f.checksum, i.title, i.summary, i.granularity,
                      c.clean_text, i.created_at
               FROM image.items i
               JOIN image.files f ON f.id = i.file_id
               LEFT JOIN LATERAL (
                   SELECT clean_text FROM image.contents
                   WHERE item_id = i.id AND is_current = true
                   ORDER BY created_at DESC LIMIT 1
               ) c ON true
               WHERE i.deleted_at IS NULL
                 AND (i.title ILIKE %s OR i.summary ILIKE %s OR c.clean_text ILIKE %s)
               ORDER BY i.created_at DESC
               LIMIT %s""",
            (like, like, like, limit),
        ).fetchall()
        entry_rows = conn.execute(
            """SELECT id AS entry_id, kind, body, created_at
               FROM core.entries
               WHERE deleted_at IS NULL AND body ILIKE %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (like, limit),
        ).fetchall()

    for r in img_rows:
        snippet = _snippet(r["clean_text"], q) if r.get("clean_text") else None
        hits.append(SearchHit(
            source="image", item_id=r["item_id"], checksum=r["checksum"],
            title=r["title"], summary=r["summary"], granularity=r["granularity"], snippet=snippet,
        ))
    for r in entry_rows:
        hits.append(SearchHit(
            source="entry", entry_id=r["entry_id"], kind=r["kind"],
            summary=r["body"][:120], snippet=_snippet(r["body"], q),
        ))
    return hits[:limit]
