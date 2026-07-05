"""维度计数:首页入口网格显示每个 theme / use 下有多少条。
另含"生长的分类":自动线攒出的新分类候选聚合 + 批量采纳。"""
from fastapi import APIRouter, Depends, Query, HTTPException

from auth import require_token
from db import get_conn
from models.items import DimensionStats, OverviewStats, ThemeCandidate, AdoptClusterResult, AdoptTheme

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_token)])


def _dict(rows: list[dict], key: str = "name") -> dict[str, int]:
    return {r[key]: r["c"] for r in rows if r[key]}


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
        domain_rows = conn.execute(
            """SELECT domain AS name, count(*) AS c FROM (
                   SELECT domain FROM image.items WHERE deleted_at IS NULL
                   UNION ALL
                   SELECT domain FROM core.entries WHERE deleted_at IS NULL
               ) x WHERE domain IS NOT NULL GROUP BY domain ORDER BY c DESC"""
        ).fetchall()
        topic_rows = conn.execute(
            """SELECT main_topic AS name, count(*) AS c FROM (
                   SELECT main_topic FROM image.items WHERE deleted_at IS NULL
                   UNION ALL
                   SELECT main_topic FROM core.entries WHERE deleted_at IS NULL
               ) x WHERE main_topic IS NOT NULL GROUP BY main_topic ORDER BY c DESC"""
        ).fetchall()
        sub_topic_rows = conn.execute(
            """SELECT sub_topic AS name, count(*) AS c FROM (
                   SELECT sub_topic FROM image.items WHERE deleted_at IS NULL
                   UNION ALL
                   SELECT sub_topic FROM core.entries WHERE deleted_at IS NULL
               ) x WHERE sub_topic IS NOT NULL GROUP BY sub_topic ORDER BY c DESC"""
        ).fetchall()
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
