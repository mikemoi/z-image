"""文字入口(core.entries)的请求/响应模型。速记/日志/计划/剪藏共用一张表,kind 区分。"""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from classification_schema import validate_topic_tree_values

KINDS = {"idea", "log", "plan"}        # 想法 / 日志 / 计划(去掉速记、剪藏并入想法)
EntryType = Literal["想法", "知识", "资料", "记录", "规则"]
Domain = Literal["身心", "生活", "能力", "财务", "方向"]
UseTag = Literal["方法", "避坑", "心态", "工具", "灵感", "存档", "决策", "参考"]
Source = Literal["我", "图片", "文件"]
FixedTopic = Literal[
    "ADHD", "情绪", "药物", "运动", "睡眠", "身体",
    "马德里", "居住", "证件", "合同", "关系", "日常",
    "西班牙语", "AI", "编程", "服务器", "产品", "学习",
    "债务", "收入", "消费", "投资", "房产", "交易",
    "目标", "底线", "规则", "决策", "复盘", "正向循环",
]
SubTopic = Literal[
    "注意力", "执行力", "拖延", "冲动", "情绪调节", "工作记忆", "时间管理", "药物配合",
    "愤怒", "焦虑", "恐惧", "烦躁", "无奈", "委屈", "低落", "自责", "羞耻", "孤独", "压力", "兴奋", "平静", "调节",
    "专注达", "褪黑素", "补剂", "剂量", "药效", "反跳", "副作用", "处方", "药盒",
    "俯卧撑", "深蹲", "卷腹", "平板支撑", "热身", "拉伸", "居家训练", "出汗", "姿态",
    "入睡", "熬夜", "早起", "睡眠质量", "午睡", "作息", "失眠",
    "皮肤", "肠胃", "疼痛", "体重", "饮食", "性健康", "体检", "疲劳",
    "交通", "EMT", "地铁", "区域", "房源", "办事", "生活便利",
    "租房", "买房", "搬家", "房间", "社区", "房东", "住家证明",
    "NIE", "居留", "护照", "社保", "Cl@ve", "政府材料",
    "租房合同", "工作合同", "服务合同", "押金", "条款", "签字",
    "朋友", "伴侣", "父母", "兄弟", "家庭", "边界", "冲突", "沟通",
    "通勤", "上班", "下班", "吃饭", "购物", "清洁", "出门", "回家", "时间线",
    "词块", "语法", "冠词", "动词", "名词", "听力", "口语", "阅读", "写作", "A1", "A2",
    "ChatGPT", "Claude", "OpenRouter", "Agent", "Prompt", "OCR", "自动化", "工作流",
    "Python", "JavaScript", "React", "FastAPI", "PostgreSQL", "Docker", "脚本", "Bug", "API",
    "VPS", "1Panel", "Nginx", "Cloudflare", "备份", "部署", "安全",
    "ZBrain", "z-image", "z-sports", "PWA", "UI", "分类系统", "内容坐标", "数据库",
    "记忆", "复习", "输入", "输出", "练习", "学习计划", "验收",
    "欠款", "还款", "朋友借钱", "止血", "风险", "清算",
    "工资", "副业", "项目收入", "技能变现", "稳定收入",
    "订阅", "冲动消费", "预算", "购买决策", "省钱", "账单",
    "ETF", "VUAA", "EQQB", "长期定投", "养老金", "股票", "组合",
    "合约", "Binance", "杠杆", "爆仓", "风控", "冲动交易", "禁止交易",
    "今日目标", "本周目标", "年度目标", "四年计划", "长期目标", "健康", "技能", "存款",
    "不新增债务", "不交易", "不伤害自己", "不冲动", "生存优先", "止损",
    "不做清单", "行为限制", "执行规则", "冲动控制", "睡眠规则", "运动规则", "消费规则",
    "已决定", "选择", "放弃", "暂缓", "路线", "优先级",
    "错误", "原因", "教训", "改进", "反面样本", "亏损复盘",
    "行动转化", "运动转化", "学习循环", "存钱循环", "睡眠循环", "自我建设", "今天完成",
    "未细分",
]


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
    sub_topic: SubTopic | None = None
    related_topics: list[FixedTopic] | None = Field(default=None, max_length=2)
    tags: list[str] | None = Field(default=None, max_length=5)
    use_tag: UseTag | None = None
    topics: list[str] | None = Field(default=None, max_length=50)
    highlights: list[str] | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def validate_topic_tree(self):
        validate_topic_tree_values(self.domain, self.main_topic, self.sub_topic, self.related_topics)
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
    sub_topic: SubTopic | None = None
    related_topics: list[FixedTopic] | None = Field(default=None, max_length=2)
    tags: list[str] | None = Field(default=None, max_length=5)
    use_tag: UseTag | None = None
    topics: list[str] | None = Field(default=None, max_length=50)
    highlights: list[str] | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def validate_topic_tree(self):
        validate_topic_tree_values(self.domain, self.main_topic, self.sub_topic, self.related_topics)
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
    sub_topic: SubTopic | None = None
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
