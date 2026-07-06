"""维度计数:首页入口网格显示每个 theme / use 下有多少条。
另含"生长的分类":自动线攒出的新分类候选聚合 + 批量采纳。"""
import json

from fastapi import APIRouter, Depends, Query, HTTPException

from auth import require_token
from db import get_conn
from models.items import (
    DimensionStats, OverviewStats, ThemeCandidate, AdoptClusterResult, AdoptTheme,
    TopicTerm, TopicTermStats, TopicTermItem, TopicTermItemList, TopicTermTrendPoint,
)

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_token)])


def _dict(rows: list[dict], key: str = "name") -> dict[str, int]:
    return {r[key]: r["c"] for r in rows if r[key]}


def _dimension_counts(conn, column: str, *, jsonb_array: bool = False,
                       main_topic: str | None = None) -> list[dict]:
    """未删除的 entries+items 按某个字段分组计数,可选按 main_topic 过滤。
    概览页(全库六个维度)和主题词频页(限定主题下的 sub_topic/tag)共用这一个构造器,
    避免每加一个维度就要在两处各写一遍 UNION ALL。
    entry_type/source 因为要做旧值别名映射(句子→想法、自己→我等),不走这里,单独写。"""
    select_expr = f"jsonb_array_elements_text({column})" if jsonb_array else column
    not_null = f" AND {column} IS NOT NULL" if jsonb_array else ""
    topic_filter = " AND main_topic = %s" if main_topic else ""
    params = (main_topic, main_topic) if main_topic else ()
    rows = conn.execute(
        f"""SELECT name, count(*) AS c FROM (
                SELECT {select_expr} AS name FROM image.items
                WHERE deleted_at IS NULL{not_null}{topic_filter}
                UNION ALL
                SELECT {select_expr} AS name FROM core.entries
                WHERE deleted_at IS NULL{not_null}{topic_filter}
            ) x WHERE name IS NOT NULL GROUP BY name ORDER BY c DESC""",
        params,
    ).fetchall()
    return rows


@router.get("/overview", response_model=OverviewStats)
async def overview():
    """统一统计截图与文字条目。只描述内容构成，不计算 streak、完成率或趋势。"""
    with get_conn() as conn:
        screenshots = conn.execute(
            "SELECT count(*) AS c FROM image.items WHERE deleted_at IS NULL"
        ).fetchone()["c"]
        kind_rows = conn.execute(
            """SELECT kind AS name, count(*) AS c FROM core.entries
               WHERE deleted_at IS NULL GROUP BY kind"""
        ).fetchall()
        type_rows = conn.execute(
            """SELECT CASE WHEN entry_type='句子' THEN '想法'
                           WHEN entry_type='决策' THEN '规则'
                           ELSE entry_type END AS name, count(*) AS c FROM (
                   SELECT entry_type FROM image.items WHERE deleted_at IS NULL
                   UNION ALL
                   SELECT entry_type FROM core.entries WHERE deleted_at IS NULL
               ) x WHERE entry_type IS NOT NULL GROUP BY name ORDER BY c DESC"""
        ).fetchall()
        domain_rows = _dimension_counts(conn, "domain")
        topic_rows = _dimension_counts(conn, "main_topic")
        sub_topic_rows = _dimension_counts(conn, "sub_topic")
        source_rows = conn.execute(
            """SELECT CASE WHEN source='自己' THEN '我'
                           WHEN source='截图' THEN '图片'
                           ELSE source END AS name, count(*) AS c FROM (
                   SELECT COALESCE(source, '图片') AS source
                   FROM image.items WHERE deleted_at IS NULL
                   UNION ALL
                   SELECT COALESCE(source, '我') AS source
                   FROM core.entries WHERE deleted_at IS NULL
               ) x WHERE source IS NOT NULL GROUP BY name"""
        ).fetchall()
        status_rows = conn.execute(
            """SELECT state AS name, count(*) AS c FROM (
                   SELECT CASE WHEN ai_classify_status = 'failed' THEN '分类失败'
                               WHEN ai_classify_status = 'done' THEN '已分类'
                               ELSE '待分类' END AS state
                   FROM image.items WHERE deleted_at IS NULL
                   UNION ALL
                   SELECT CASE WHEN ai_classify_status = 'failed' THEN '分类失败'
                               WHEN ai_classify_status = 'done' THEN '已分类'
                               ELSE '待分类' END AS state
                   FROM core.entries WHERE deleted_at IS NULL
               ) x GROUP BY state"""
        ).fetchall()

    kinds = _dict(kind_rows)
    contents = {
        "截图": screenshots,
        "想法": kinds.get("idea", 0),
        "日志": kinds.get("log", 0),
        "长期计划": kinds.get("plan", 0),
    }
    if kinds.get("memo", 0):
        contents["近日"] = kinds["memo"]
    total = screenshots + sum(kinds.values())
    return OverviewStats(
        total=total, contents=contents, entry_types=_dict(type_rows),
        domains=_dict(domain_rows), main_topics=_dict(topic_rows),
        sub_topics=_dict(sub_topic_rows), sources=_dict(source_rows),
        classify_statuses=_dict(status_rows),
    )


@router.get("/dimensions", response_model=DimensionStats)
async def dimensions():
    """只统计未删除、已分类(theme/use 非空)的条目。"""
    with get_conn() as conn:
        total = conn.execute(
            "SELECT count(*) AS c FROM image.items WHERE deleted_at IS NULL"
        ).fetchone()["c"]
        assets = conn.execute(
            "SELECT count(*) AS c FROM image.items WHERE deleted_at IS NULL AND granularity = 'asset'"
        ).fetchone()["c"]
        theme_rows = conn.execute(
            """SELECT theme, count(*) AS c FROM image.items
               WHERE deleted_at IS NULL AND theme IS NOT NULL
               GROUP BY theme"""
        ).fetchall()
        use_rows = conn.execute(
            """SELECT use_tag, count(*) AS c FROM image.items
               WHERE deleted_at IS NULL AND use_tag IS NOT NULL
               GROUP BY use_tag"""
        ).fetchall()

    return DimensionStats(
        total=total,
        assets=assets,
        themes={r["theme"]: r["c"] for r in theme_rows},
        uses={r["use_tag"]: r["c"] for r in use_rows},
    )


@router.get("/theme-candidates", response_model=list[ThemeCandidate])
async def theme_candidates(min: int = Query(default=3, ge=2, le=50)):
    """自动线攒出的新分类候选:AI 判了 suggested_theme、但还没被采纳(theme≠该候选),
    按频次聚合、达到 min 才冒出来。不逐条推,是"攒够一簇才问一次"。"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ai_output->>'suggested_theme' AS name, count(*) AS c
               FROM image.items
               WHERE deleted_at IS NULL
                 AND ai_output->>'suggested_theme' IS NOT NULL
                 AND ai_output->>'suggested_theme' <> ''
                 AND theme IS DISTINCT FROM ai_output->>'suggested_theme'
               GROUP BY 1
               HAVING count(*) >= %s
               ORDER BY c DESC, name""",
            (min,),
        ).fetchall()
    return [ThemeCandidate(name=r["name"], count=r["c"]) for r in rows]


@router.get("/topic-terms", response_model=TopicTermStats)
async def topic_terms(main_topic: str = Query(...)):
    """某主题(如"交易")下,子题 + 标签的出现频率榜。不含候选池,只统计已定型的分类结果。
    "未细分"是兜底桶,不是真实词,排除在榜单外。"""
    with get_conn() as conn:
        total = conn.execute(
            """SELECT count(*) AS c FROM (
                   SELECT 1 FROM image.items WHERE deleted_at IS NULL AND main_topic = %s
                   UNION ALL
                   SELECT 1 FROM core.entries WHERE deleted_at IS NULL AND main_topic = %s
               ) x""",
            (main_topic, main_topic),
        ).fetchone()["c"]
        sub_topic_rows = _dimension_counts(conn, "sub_topic", main_topic=main_topic)
        tag_rows = _dimension_counts(conn, "tags", jsonb_array=True, main_topic=main_topic)

    terms = [TopicTerm(term=r["name"], type="sub_topic", count=r["c"])
             for r in sub_topic_rows if r["name"] != "未细分"]
    terms += [TopicTerm(term=r["name"], type="tag", count=r["c"]) for r in tag_rows]
    terms.sort(key=lambda t: t.count, reverse=True)
    return TopicTermStats(main_topic=main_topic, total=total, terms=terms)


@router.get("/topic-terms/items", response_model=TopicTermItemList)
async def topic_term_items(
    main_topic: str = Query(...),
    term: str = Query(...),
    type: str = Query(..., pattern="^(sub_topic|tag)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """点某个子题/标签,看命中的原文(截图详情 or 手写条目),按时间倒序。"""
    if type == "sub_topic":
        item_filter, item_params = "i.sub_topic = %s", (term,)
        entry_filter, entry_params = "e.sub_topic = %s", (term,)
    else:
        tag_json = json.dumps([term])
        item_filter, item_params = "i.tags @> %s::jsonb", (tag_json,)
        entry_filter, entry_params = "e.tags @> %s::jsonb", (tag_json,)

    with get_conn() as conn:
        total = conn.execute(
            f"""SELECT count(*) AS c FROM (
                   SELECT 1 FROM image.items i WHERE i.deleted_at IS NULL AND i.main_topic = %s AND {item_filter}
                   UNION ALL
                   SELECT 1 FROM core.entries e WHERE e.deleted_at IS NULL AND e.main_topic = %s AND {entry_filter}
               ) x""",
            (main_topic, *item_params, main_topic, *entry_params),
        ).fetchone()["c"]
        rows = conn.execute(
            f"""SELECT * FROM (
                   SELECT 'item' AS source, i.id, NULL AS kind, i.title, i.summary,
                          f.checksum, i.created_at
                   FROM image.items i JOIN image.files f ON f.id = i.file_id
                   WHERE i.deleted_at IS NULL AND i.main_topic = %s AND {item_filter}
                   UNION ALL
                   SELECT 'entry' AS source, e.id, e.kind, NULL AS title, e.body AS summary,
                          NULL AS checksum, e.created_at
                   FROM core.entries e
                   WHERE e.deleted_at IS NULL AND e.main_topic = %s AND {entry_filter}
               ) x ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            (main_topic, *item_params, main_topic, *entry_params, limit, offset),
        ).fetchall()

    return TopicTermItemList(total=total, items=[TopicTermItem(**r) for r in rows])


@router.get("/topic-terms/trend", response_model=list[TopicTermTrendPoint])
async def topic_term_trend(
    main_topic: str = Query(...),
    term: str = Query(...),
    type: str = Query(..., pattern="^(sub_topic|tag)$"),
    granularity: str = Query(default="week", pattern="^(week|month)$"),
):
    """某个子题/标签随时间(周/月)的出现次数,看最近是不是讨论变多/变少。"""
    if type == "sub_topic":
        item_filter, item_params = "sub_topic = %s", (term,)
        entry_filter, entry_params = "sub_topic = %s", (term,)
    else:
        tag_json = json.dumps([term])
        item_filter, item_params = "tags @> %s::jsonb", (tag_json,)
        entry_filter, entry_params = "tags @> %s::jsonb", (tag_json,)

    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT date_trunc(%s, created_at) AS period, count(*) AS c FROM (
                   SELECT created_at FROM image.items
                   WHERE deleted_at IS NULL AND main_topic = %s AND {item_filter}
                   UNION ALL
                   SELECT created_at FROM core.entries
                   WHERE deleted_at IS NULL AND main_topic = %s AND {entry_filter}
               ) x GROUP BY period ORDER BY period""",
            (granularity, main_topic, *item_params, main_topic, *entry_params),
        ).fetchall()

    return [TopicTermTrendPoint(period=r["period"], count=r["c"]) for r in rows]


@router.post("/theme-candidates/adopt", response_model=AdoptClusterResult)
async def adopt_candidate(body: AdoptTheme):
    """批量采纳一簇候选:建 theme tag + 把整簇(suggested_theme=该名、尚未归入)一次归入。"""
    name = (body.theme or "").strip()
    if not name:
        raise HTTPException(400, "theme required")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO core.tags (name, kind) VALUES (%s, 'theme') ON CONFLICT DO NOTHING",
            (name,),
        )
        rows = conn.execute(
            """UPDATE image.items SET theme = %s, updated_at = now()
               WHERE deleted_at IS NULL
                 AND ai_output->>'suggested_theme' = %s
                 AND theme IS DISTINCT FROM %s
               RETURNING id""",
            (name, name, name),
        ).fetchall()
        conn.commit()
    return AdoptClusterResult(theme=name, count=len(rows))
