"""items 相关的响应/请求模型。第二步只需基础字段。"""
from datetime import datetime
from pydantic import BaseModel


class UploadResult(BaseModel):
    received: int
    message: str


class ItemBrief(BaseModel):
    """列表卡片用的精简字段。"""
    id: int
    file_id: int
    checksum: str
    status: str
    title: str | None = None
    summary: str | None = None
    theme: str | None = None
    use_tag: str | None = None
    granularity: str | None = None
    reviewed_at: datetime | None = None
    promoted_at: datetime | None = None
    created_at: datetime


class ItemDetail(ItemBrief):
    """详情页:在精简字段上补齐原图与正文。"""
    original_filename: str
    is_ocr_suitable: bool | None = None
    clean_text: str | None = None
    raw_text: str | None = None


class ItemList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ItemBrief]


class ItemUpdate(BaseModel):
    """改标签:所有字段可选,只更新传入的。"""
    title: str | None = None
    theme: str | None = None
    use_tag: str | None = None
    status: str | None = None
    granularity: str | None = None


class DimensionStats(BaseModel):
    total: int
    themes: dict[str, int]
    uses: dict[str, int]


class PromoteResult(BaseModel):
    ok: bool = True
    knowledge_ids: list[int]
    count: int


class NoteResult(BaseModel):
    ok: bool = True
    note_id: int


class ResurfaceNote(BaseModel):
    id: int
    body: str
    use_tag: str | None = None
    checksum: str | None = None       # 来源图缩略,可空(手敲的没有)
    last_seen_at: datetime | None = None


class KnowledgeHit(BaseModel):
    id: int
    title: str | None = None
    body: str
    summary: str | None = None
    checksum: str | None = None
    created_at: datetime


class OkResult(BaseModel):
    ok: bool = True
