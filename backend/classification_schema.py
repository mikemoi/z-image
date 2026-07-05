"""Final content-coordinate constants and normalizers."""

ENTRY_TYPES = {"想法", "知识", "资料", "记录", "规则"}
ENTRY_TYPE_ALIASES = {
    "句子": "想法",
    "决策": "规则",
}

DOMAINS = {"身心", "生活", "能力", "财务", "方向"}
TOPICS_BY_DOMAIN = {
    "身心": ["ADHD", "情绪", "药物", "运动", "睡眠", "身体"],
    "生活": ["马德里", "居住", "证件", "合同", "关系", "日常"],
    "能力": ["西班牙语", "AI", "编程", "服务器", "产品", "学习"],
    "财务": ["债务", "收入", "消费", "投资", "房产", "交易"],
    "方向": ["目标", "底线", "规则", "决策", "复盘", "正向循环"],
}
FIXED_TOPICS = {topic for values in TOPICS_BY_DOMAIN.values() for topic in values}

SUB_TOPICS_BY_TOPIC = {
    "ADHD": ["注意力", "执行力", "拖延", "冲动", "情绪调节", "工作记忆", "时间管理", "药物配合", "未细分"],
    "情绪": ["愤怒", "焦虑", "恐惧", "烦躁", "无奈", "委屈", "低落", "自责", "羞耻", "孤独", "压力", "兴奋", "平静", "调节", "未细分"],
    "药物": ["专注达", "褪黑素", "补剂", "剂量", "药效", "反跳", "副作用", "处方", "药盒", "未细分"],
    "运动": ["俯卧撑", "深蹲", "卷腹", "平板支撑", "热身", "拉伸", "居家训练", "出汗", "姿态", "未细分"],
    "睡眠": ["入睡", "熬夜", "早起", "睡眠质量", "午睡", "作息", "失眠", "褪黑素", "未细分"],
    "身体": ["皮肤", "肠胃", "疼痛", "体重", "饮食", "性健康", "体检", "疲劳", "未细分"],
    "马德里": ["交通", "EMT", "地铁", "区域", "房源", "办事", "生活便利", "未细分"],
    "居住": ["租房", "买房", "搬家", "房间", "社区", "房东", "住家证明", "未细分"],
    "证件": ["NIE", "居留", "护照", "社保", "Cl@ve", "住家证明", "政府材料", "未细分"],
    "合同": ["租房合同", "工作合同", "服务合同", "押金", "条款", "签字", "未细分"],
    "关系": ["朋友", "伴侣", "父母", "兄弟", "家庭", "边界", "冲突", "沟通", "未细分"],
    "日常": ["通勤", "上班", "下班", "吃饭", "购物", "清洁", "出门", "回家", "时间线", "未细分"],
    "西班牙语": ["词块", "语法", "冠词", "动词", "名词", "听力", "口语", "阅读", "写作", "A1", "A2", "未细分"],
    "AI": ["ChatGPT", "Claude", "OpenRouter", "Agent", "Prompt", "OCR", "自动化", "工作流", "未细分"],
    "编程": ["Python", "JavaScript", "React", "FastAPI", "PostgreSQL", "Docker", "脚本", "Bug", "API", "未细分"],
    "服务器": ["VPS", "1Panel", "Nginx", "Cloudflare", "Docker", "备份", "部署", "安全", "未细分"],
    "产品": ["ZBrain", "z-image", "z-sports", "PWA", "UI", "分类系统", "内容坐标", "数据库", "未细分"],
    "学习": ["阅读", "记忆", "复习", "输入", "输出", "练习", "学习计划", "验收", "未细分"],
    "债务": ["欠款", "还款", "朋友借钱", "止血", "风险", "清算", "未细分"],
    "收入": ["工资", "副业", "项目收入", "技能变现", "稳定收入", "未细分"],
    "消费": ["订阅", "冲动消费", "预算", "购买决策", "省钱", "账单", "未细分"],
    "投资": ["ETF", "VUAA", "EQQB", "长期定投", "养老金", "股票", "组合", "风险", "未细分"],
    "房产": ["买房", "卖房", "房贷", "估值", "Nota Simple", "区域", "产权", "赠与", "未细分"],
    "交易": ["合约", "Binance", "杠杆", "爆仓", "风控", "冲动交易", "复盘", "禁止交易", "未细分"],
    "目标": ["今日目标", "本周目标", "年度目标", "四年计划", "长期目标", "健康", "技能", "存款", "未细分"],
    "底线": ["不新增债务", "不交易", "不伤害自己", "不冲动", "生存优先", "止损", "未细分"],
    "规则": ["不做清单", "行为限制", "执行规则", "冲动控制", "睡眠规则", "运动规则", "消费规则", "未细分"],
    "决策": ["已决定", "选择", "放弃", "暂缓", "路线", "优先级", "未细分"],
    "复盘": ["错误", "原因", "教训", "改进", "反面样本", "亏损复盘", "未细分"],
    "正向循环": ["行动转化", "运动转化", "学习循环", "存钱循环", "睡眠循环", "自我建设", "今天完成", "未细分"],
}

SOURCES = {"我", "图片", "文件"}
SOURCE_ALIASES = {
    "自己": "我",
    "截图": "图片",
}


def normalize_entry_type(value: str | None) -> str | None:
    value = (value or "").strip()
    value = ENTRY_TYPE_ALIASES.get(value, value)
    return value if value in ENTRY_TYPES else None


def normalize_source(value: str | None, fallback: str | None = None) -> str | None:
    value = (value or fallback or "").strip()
    value = SOURCE_ALIASES.get(value, value)
    return value if value in SOURCES else None


def normalize_sub_topic(main_topic: str | None, sub_topic: str | None) -> str | None:
    if not main_topic:
        return None
    value = (sub_topic or "").strip() or "未细分"
    allowed = SUB_TOPICS_BY_TOPIC.get(main_topic, [])
    return value if value in allowed else "未细分"


def validate_topic_tree_values(domain, main_topic, sub_topic=None, related_topics=None):
    """Validate final content-coordinate tree values."""
    if domain and domain not in TOPICS_BY_DOMAIN:
        raise ValueError("domain 必须是固定领域")
    if domain and main_topic and main_topic not in TOPICS_BY_DOMAIN[domain]:
        raise ValueError("主题必须属于所选领域")
    if main_topic and sub_topic and sub_topic not in SUB_TOPICS_BY_TOPIC.get(main_topic, []):
        raise ValueError("子题必须属于所选主题")
    related = related_topics or []
    if any(topic not in FIXED_TOPICS for topic in related):
        raise ValueError("相关只能使用固定主题")
    if len(related) != len(set(related)):
        raise ValueError("相关不能重复")
    if main_topic and main_topic in related:
        raise ValueError("相关不能包含主题")
