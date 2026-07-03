"""全文检索:走 core.knowledge 的 body_tsv(title+body)。零额外成本。"""
from fastapi import APIRouter, Depends, Query

from auth import require_token
from db import get_conn
from models.items import KnowledgeHit

router = APIRouter(prefix="/api/search", tags=["search"], dependencies=[Depends(require_token)])


@router.get("", response_model=list[KnowledgeHit])
async def search(q: str = Query(..., min_length=1), limit: int = Query(default=30, le=100)):
    """按关键词检索精选脑。simple 分词,plainto 兜底任意输入。"""
    with get_conn() as conn:
        # 中文无空格,tsvector('simple') 会把整段当一个 token → 补 ILIKE 子串兜底。
        like = f"%{q}%"
        rows = conn.execute(
            """SELECT k.id, k.title, k.body, k.summary, k.created_at, f.checksum
               FROM core.knowledge k
               LEFT JOIN core.sources s ON s.id = k.source_id
               LEFT JOIN image.files f
                      ON f.id = s.origin_id AND s.origin_schema = 'image' AND s.origin_table = 'files'
               WHERE k.deleted_at IS NULL
                 AND (k.body_tsv @@ plainto_tsquery('simple', %s)
                      OR k.body ILIKE %s OR k.title ILIKE %s)
               ORDER BY ts_rank(k.body_tsv, plainto_tsquery('simple', %s)) DESC,
                        k.created_at DESC
               LIMIT %s""",
            (q, like, like, q, limit),
        ).fetchall()
    return [KnowledgeHit(**r) for r in rows]
