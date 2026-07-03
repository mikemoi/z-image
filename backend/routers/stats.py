"""维度计数:首页入口网格显示每个 theme / use 下有多少条。"""
from fastapi import APIRouter, Depends

from auth import require_token
from db import get_conn
from models.items import DimensionStats

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
