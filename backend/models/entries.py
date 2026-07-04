"""文字入口(core.entries)的请求/响应模型。速记/日志/计划/剪藏共用一张表,kind 区分。"""
from datetime import date, datetime
from pydantic import BaseModel

KINDS = {"note", "log", "plan", "clip"}


class EntryCreate(BaseModel):
    kind: str = "note"                 # note速记 | log日志 | plan计划 | clip剪藏
    body: str
    mood: str | None = None            # 日志可选心情
    logged_for: date | None = None     # 日志:事情发生的日期,缺省=今天
    pinned: bool = False               # 计划钉住


class EntryUpdate(BaseModel):
    body: str | None = None
    mood: str | None = None
    pinned: bool | None = None
    status: str | None = None
    logged_for: date | None = None


class Entry(BaseModel):
    id: int
    kind: str
    body: str
    status: str
    mood: str | None = None
    pinned: bool = False
    logged_for: date | None = None
    created_at: datetime
    updated_at: datetime


class FileEntry(BaseModel):
    """归位:把 inbox 里的文字沉进精选脑。"""
    target: str = "note"               # note → core.notes(轻) | knowledge → core.knowledge(切块)


class FileResult(BaseModel):
    ok: bool = True
    target: str
    count: int = 1


class CleanupItem(BaseModel):
    """清库仪式:AI 顺手判为『无信息量』的条目(主动进入才聚合,不推送、不计数)。"""
    id: int
    checksum: str
    title: str | None = None
    summary: str | None = None
    quality_note: str | None = None
