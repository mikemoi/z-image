"""缩略图:上传时顺手生成一张定长边 JPEG,列表/批阅用它省流量;详情页/放大仍用原图。

对老图(功能上线前已上传的)缺缩略图时,files 路由按需现生成一次再返回,
不需要额外的存量回填任务。生成失败(非图片/文件损坏)时静默跳过,调用方回退用原图。
"""
from pathlib import Path

from PIL import Image, UnidentifiedImageError

THUMB_MAX_EDGE = 960
THUMB_QUALITY = 78


def thumb_path_for(original_path: Path) -> Path:
    return original_path.with_name(f"{original_path.stem}_thumb.jpg")


def ensure_thumbnail(original_path: Path) -> Path | None:
    """确保原图对应的缩略图存在,返回缩略图路径;生成失败返回 None(调用方应回退用原图)。"""
    thumb_path = thumb_path_for(original_path)
    if thumb_path.exists():
        return thumb_path
    try:
        with Image.open(original_path) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE), Image.Resampling.LANCZOS)
            im.save(thumb_path, "JPEG", quality=THUMB_QUALITY)
        return thumb_path
    except (UnidentifiedImageError, OSError):
        return None
