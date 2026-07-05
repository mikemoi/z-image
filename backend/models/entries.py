"""文字入口(core.entries)的请求/响应模型。速记/日志/计划/剪藏共用一张表,kind 区分。"""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator

KINDS = {"idea", "log", "plan"}        # 想法 / 日志 / 计划(去掉速记、剪藏并入想法)
EntryType = Literal["想法", "句子", "规则", "决策", "知识", "资料", "记录"]
Domain = Literal["身心", "生活", "能力", "财务", "方向"]
UseTag = Literal["方法", "避坑", "心态", "工具", "灵感", "存档", "决策", "参考"]
Source = Literal["自己", "截图", "文件"]
FixedTopic = Literal[
    "ADHD", "情绪", "药物", "运动", "睡眠", "身体",
    "马德里", "居住", "证件", "合同", "关系", "日常",
    "西班牙语", "AI", "编程", "服务器", "产品", "学习",
    "债务", "收入", "消费", "投资", "房产", "交易",
    "目标", "底线", "规则", "决策", "复盘", "正向循环",
]
TOPICS_BY_DOMAIN = {
    "身心": {"ADHD", "情绪", "药物", "运动", "睡眠", "身体"},
    "生活": {"马德里", "居住", "证件", "合同", "关系", "日常"},
    "能力": {"西班牙语", "AI", "编程", "服务器", "产品", "学习"},
    "财务": {"债务", "收入", "消费", "投资", "房产", "交易"},
    "方向": {"目标", "底线", "规则", "决策", "复盘", "正向循环"},
}


def _validate_topics(domain, main_topic, related_topics):
    if domain and main_topic and main_topic not in TOPICS_BY_DOMAIN[domain]:
        raise ValueError("main_topic 必须属于所选 domain")
    related = related_topics or []
    if len(related) != len(set(related)):
        raise ValueError("related_topics 不能重复")
    if main_topic and main_topic in related:
        raise ValueError("related_topics 不能包含 main_topic")


class EntryCreate(BaseModel):
    kind: str = "idea"                 # idea想法 | log日志 | plan计划
    body: str
    mood: str | None = None            # 日志可选心情
    logged_for: date | None = None     # 日志:事情发生的日期,缺省=今天
    pinned: bool = False               # 计划钉住
    source_item_id: int | None = None  # 想法来自哪张截图(可空=凭空记的)
    entry_type: EntryType | None = None
    domain: Domain | None = None
    main_topic: FixedTopic | None = None
    related_topics: list[FixedTopic] | None = Field(default=None, max_length=2)
    tags: list[str] | None = Field(default=None, max_length=5)
    use_tag: UseTag | None = None
    topics: list[str] | None = Field(default=None, max_length=50)
    highlights: list[str] | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def validate_topic_tree(self):
        _validate_topics(self.domain, self.main_topic, self.related_topics)
        return self


class EntryUpdate(BaseModel):
    body: str | None = None
    mood: str | None = None
    pinned: bool | None = None
    status: str | None = None
    logged_for: date | None = None
    theme: str | None = None
    entry_type: EntryType | None = None
    domain: Domain | None = None
    main_topic: FixedTopic | None = None
    related_topics: list[FixedTopic] | None = Field(default=None, max_length=2)
    tags: list[str] | None = Field(default=None, max_length=5)
    use_tag: UseTag | None = None
    topics: list[str] | None = Field(default=None, max_length=50)
    highlights: list[str] | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def validate_topic_tree(self):
        _validate_topics(self.domain, self.main_topic, self.related_topics)
        return self


class Entry(BaseModel):
    id: int
    kind: str
    body: str
    status: str
    mood: str | None = None
    pinned: bool = False
    logged_for: date | None = None
    source_item_id: int | None = None
    theme: str | None = None
    promoted_at: datetime | None = None
    entry_type: EntryType | None = None
    domain: Domain | None = None
    main_topic: FixedTopic | None = None
    related_topics: list[FixedTopic] | None = None
    tags: list[str] | None = None
    use_tag: UseTag | None = None
    source: Source | None = None
    topics: list[str] | None = None
    highlights: list[str] | None = None
    ai_classify_status: str | None = None
    ai_classified_at: datetime | None = None
    ai_classify_output: dict | None = None
    checksum: str | None = None        # 想法来源截图缩略(ideas 列表用)
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
