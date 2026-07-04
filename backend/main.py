"""zbrain 后端入口。API + 后台 worker + 可选挂载前端 dist。"""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from db import open_pool, close_pool, check_db, ensure_schema
from auth import require_token
from routers import items, files, stats, feed, search, entries
from worker import start_worker, stop_worker, budget_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    ensure_schema()
    start_worker()
    yield
    await stop_worker()
    close_pool()


app = FastAPI(title="zbrain", version="0.1.0", lifespan=lifespan)

# 单用户自用,前端与后端分离开发期放开 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(items.router)
app.include_router(files.router)
app.include_router(stats.router)
app.include_router(feed.router)
app.include_router(search.router)
app.include_router(entries.router)


@app.get("/api/health")
async def health():
    """无需鉴权:探活 + DB 连通性。"""
    return {"status": "ok", "db": "connected" if check_db() else "disconnected"}


@app.get("/api/whoami")
async def whoami(_: bool = Depends(require_token)):
    """需鉴权:验证 token 通路。"""
    return {"status": "ok", "authenticated": True}


@app.get("/api/worker/status")
async def worker_status(_: bool = Depends(require_token)):
    """当日 Vision 预算使用情况。"""
    return budget_status()


# ── 挂载前端 dist(存在才挂;API 路由已在上面注册,优先匹配) ──────────────────
_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        """静态文件直出;其余路径回退 index.html 交给前端路由。"""
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
