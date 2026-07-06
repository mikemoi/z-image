"""原图/缩略图服务:按 checksum 返回磁盘文件,供前端与 iPhone 展示。"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from auth import require_token
from db import get_conn
from thumbnail import ensure_thumbnail

router = APIRouter(prefix="/api/files", tags=["files"], dependencies=[Depends(require_token)])

# checksum 即内容指纹,同一 checksum 的字节永远不变,可放心长期缓存。
_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}


@router.get("/{checksum}")
async def get_file(checksum: str, thumb: bool = Query(default=False)):
    """按 checksum 取原图;thumb=true 取列表用缩略图,缺失时按需现生成一次,失败则回退原图。"""
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
    serve_path = path
    if thumb:
        generated = ensure_thumbnail(path)
        if generated is not None:
            serve_path = generated
    return FileResponse(serve_path, content_disposition_type="inline", headers=_CACHE_HEADERS)
