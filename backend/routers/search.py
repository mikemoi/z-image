"""全文检索:覆盖全部上传条目(标题/摘要/正文),不再只搜"已入脑"的。

修复:旧版只查 core.knowledge,而用户基本不入脑 → 搜什么都空、证件永远搜不到。
现在直接搜 image.items(未删),中文无空格走 ILIKE 子串,零额外成本、几千条足够快。
"""
from fastapi import APIRouter, Depends, Query

from auth import require_token
from db import get_conn
from models.items import SearchHit
from classification_schema import normalize_entry_type, normalize_source

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


def _escape_like(s: str) -> str:
    """转义 ILIKE 模式里的字面 % 和 _ (含反斜杠本身),避免用户搜"100%"这类内容时被当成通配符。"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _scope_sql(alias: str, scope: str) -> str:
    source = f"COALESCE({alias}.source, '')"
    if scope == "mine":
        return f" AND {source} IN ('我', '自己')"
    if scope == "external":
        return f" AND {source} IN ('图片', '截图', '文件')"
    return ""


@router.get("", response_model=list[SearchHit])
async def search(
    q: str = Query(..., min_length=1),
    scope: str = Query(default="all", pattern="^(all|mine|external)$"),
    limit: int = Query(default=50, le=200),
):
    """按关键词检索全部截图条目(标题/摘要/正文)+ 手写文字(速记/日志/计划/剪藏)。"""
    like = f"%{_escape_like(q)}%"
    with get_conn() as conn:
        img_rows = conn.execute(
            """SELECT i.id AS item_id, f.checksum, i.title, i.summary, i.granularity,
                      c.clean_text, i.entry_type, i.domain, i.main_topic, i.sub_topic,
                      i.related_topics, COALESCE(i.tags, i.topics) AS tags,
                      COALESCE(i.source, '图片') AS source_label, i.created_at
               FROM image.items i
               JOIN image.files f ON f.id = i.file_id
               LEFT JOIN LATERAL (
                   SELECT clean_text FROM image.contents
                   WHERE item_id = i.id AND is_current = true
                   ORDER BY created_at DESC LIMIT 1
               ) c ON true
               WHERE i.deleted_at IS NULL
                 AND (i.title ILIKE %s OR i.summary ILIKE %s OR c.clean_text ILIKE %s)
                 """ + _scope_sql("i", scope) + """
               ORDER BY i.created_at DESC
               LIMIT %s""",
            (like, like, like, limit),
        ).fetchall()
        entry_rows = conn.execute(
            """SELECT id AS entry_id, kind, body, entry_type, domain, main_topic, sub_topic,
                      related_topics, COALESCE(tags, topics) AS tags,
                      COALESCE(source, '我') AS source_label, created_at
               FROM core.entries
               WHERE deleted_at IS NULL AND body ILIKE %s
                 """ + _scope_sql("core.entries", scope) + """
               ORDER BY created_at DESC
               LIMIT %s""",
            (like, limit),
        ).fetchall()

    # 两路各按 limit 取够候选后在内存按时间合并,再统一截断;
    # 避免图片命中天然更多时把文字命中挤出结果之外。
    combined = [("image", r) for r in img_rows] + [("entry", r) for r in entry_rows]
    combined.sort(key=lambda pair: pair[1]["created_at"], reverse=True)

    hits: list[SearchHit] = []
    for kind, r in combined[:limit]:
        if kind == "image":
            snippet = _snippet(r["clean_text"], q) if r.get("clean_text") else None
            hits.append(SearchHit(
                source="image", item_id=r["item_id"], checksum=r["checksum"],
                title=r["title"], summary=r["summary"], granularity=r["granularity"], snippet=snippet,
                entry_type=normalize_entry_type(r.get("entry_type")), domain=r.get("domain"),
                main_topic=r.get("main_topic"), sub_topic=r.get("sub_topic"),
                related_topics=r.get("related_topics"), tags=r.get("tags"),
                source_label=normalize_source(r.get("source_label"), "图片"),
            ))
        else:
            hits.append(SearchHit(
                source="entry", entry_id=r["entry_id"], kind=r["kind"],
                summary=r["body"][:120], snippet=_snippet(r["body"], q),
                entry_type=normalize_entry_type(r.get("entry_type")), domain=r.get("domain"),
                main_topic=r.get("main_topic"), sub_topic=r.get("sub_topic"),
                related_topics=r.get("related_topics"), tags=r.get("tags"),
                source_label=normalize_source(r.get("source_label"), "我"),
            ))
    return hits
