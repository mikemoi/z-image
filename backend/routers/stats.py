"""维度计数:首页入口网格显示每个 theme / use 下有多少条。
另含"生长的分类":自动线攒出的新分类候选聚合 + 批量采纳。"""
from fastapi import APIRouter, Depends, Query, HTTPException

from auth import require_token
from db import get_conn
from models.items import DimensionStats, ThemeCandidate, AdoptClusterResult, AdoptTheme

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_token)])


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
