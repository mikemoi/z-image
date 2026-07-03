"""原图服务:按 checksum 返回磁盘原文件,供前端与 iPhone 展示。"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from auth import require_token
from db import get_conn

router = APIRouter(prefix="/api/files", tags=["files"], dependencies=[Depends(require_token)])


@router.get("/{checksum}")
async def get_file(checksum: str):
    """按 checksum 取原图。返回磁盘文件,由浏览器按类型渲染。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT file_path, original_filename FROM image.files WHERE checksum = %s LIMIT 1",
            (checksum,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "file not found")
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(410, "file record exists but disk file is gone")
    return FileResponse(path, content_disposition_type="inline")
