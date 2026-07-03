"""zbrain 后端入口。第一步只做地基:健康检查 + 鉴权。"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from db import open_pool, close_pool, check_db
from auth import require_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    yield
    close_pool()


app = FastAPI(title="zbrain", version="0.1.0", lifespan=lifespan)

# 单用户自用,前端与后端分离开发期放开 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """无需鉴权:探活 + DB 连通性。"""
    return {"status": "ok", "db": "connected" if check_db() else "disconnected"}


@app.get("/api/whoami")
async def whoami(_: bool = Depends(require_token)):
    """需鉴权:验证 token 通路。"""
    return {"status": "ok", "authenticated": True}
