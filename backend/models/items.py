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
    entry_type: str | None = None
    domain: str | None = None
    topics: list[str] | None = None
    ai_classify_status: str | None = None
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
    entry_type: str | None = None
    domain: str | None = None
    topics: list[str] | None = None


class DimensionStats(BaseModel):
    total: int
    assets: int = 0                     # granularity='asset' 的资料数
    themes: dict[str, int]
    uses: dict[str, int]


class OverviewStats(BaseModel):
    """“我的 → 数据概览”使用的统一内容构成。"""
    total: int
    contents: dict[str, int]
    entry_types: dict[str, int]
    domains: dict[str, int]
    uses: dict[str, int]
    sources: dict[str, int]
    classify_statuses: dict[str, int]


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


class SearchHit(BaseModel):
    """搜索命中:覆盖全部上传条目 + 手写文字(速记/日志/计划/剪藏)。source 区分,前端分流跳转。"""
    source: str = "image"            # 'image' 截图条目 | 'entry' 手写文字
    item_id: int | None = None       # image:点进详情看原图
    checksum: str | None = None
    entry_id: int | None = None      # entry:点进对应文字页
    kind: str | None = None          # entry 的 kind(note/log/plan/clip)
    title: str | None = None
    summary: str | None = None
    granularity: str | None = None
    snippet: str | None = None       # 正文里命中词周围的片段,可空


class InsightResult(BaseModel):
    """「问问 AI」的看法。明确是 AI 补充,与原文事实源分开。按需生成、结果缓存。"""
    explanation: str                          # 讲明白 + 一句看法/定义
    quality: str | None = None                # 干货 / 反面样本 / 无信息量
    quality_note: str | None = None           # 为什么这么判断
    suggested_theme: str | None = None         # 现有分类都不合适时,提议的新分类名
    suggested_theme_reason: str | None = None
    cached: bool = False                      # 是否命中缓存(未重新烧钱)


class AdoptTheme(BaseModel):
    """采纳 AI 提议的新分类:建 tag + 打到本条上(生长的分类,你点头才生效)。"""
    theme: str


class ThemeCandidate(BaseModel):
    """自动线攒出的新分类候选:一簇被 AI 判为同一新领域的条目。"""
    name: str
    count: int


class AdoptClusterResult(BaseModel):
    """批量采纳一簇候选:建 tag + 把整簇条目归入。"""
    ok: bool = True
    theme: str
    count: int


class OkResult(BaseModel):
    ok: bool = True
