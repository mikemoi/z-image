"""AI 自动分类:类型 + 领域 + 固定主题 + 少量标签(source 由入口确定)。

枚举严格固定(见 models/entries.py 的 Literal);prompt 把固定值+含义全给模型,只能选里面的,
后端再 normalize 校验一遍；AI 只能归类，不能扩建固定体系。
"""
import json
import re

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, VISION_MODEL

ENTRY_TYPES = {"想法", "句子", "规则", "决策", "知识", "资料", "记录"}
DOMAINS = {"身心", "生活", "能力", "财务", "方向"}
TOPICS_BY_DOMAIN = {
    "身心": ["ADHD", "情绪", "药物", "运动", "睡眠", "身体"],
    "生活": ["马德里", "居住", "证件", "合同", "关系", "日常"],
    "能力": ["西班牙语", "AI", "编程", "服务器", "产品", "学习"],
    "财务": ["债务", "收入", "消费", "投资", "房产", "交易"],
    "方向": ["目标", "底线", "规则", "决策", "复盘", "正向循环"],
}
FIXED_TOPICS = {topic for values in TOPICS_BY_DOMAIN.values() for topic in values}

PROMPT = """你是一个个人第二脑的内容分类器。给你一段文字,请按固定体系归类。
只返回一个 JSON 对象,不要解释、不要 markdown 包裹。

1. entry_type(类型,择一):
   想法=我的理解/判断/感悟  句子=认可并想保存的一句话  规则=以后要执行的行为准则
   决策=已经确定的选择  知识=可学习可复用的信息  资料=合同/证件/药盒/票据/配置等材料
   记录=当时发生的事/状态/情绪/体验/时间线
2. domain(领域,择一):
   身心=情绪/ADHD/药物/运动/睡眠/身体/健康  生活=马德里/居住/合同/证件/家庭/日常/办事
   能力=西班牙语/AI/编程/项目/服务器/学习/写作  财务=债务/收入/消费/投资/房产/交易/风控/养老金
   方向=目标/底线/规则/长期规划/正向循环/人生策略
3. main_topic(主主题,择一且必须属于所选领域):
   身心: ADHD/情绪/药物/运动/睡眠/身体
   生活: 马德里/居住/证件/合同/关系/日常
   能力: 西班牙语/AI/编程/服务器/产品/学习
   财务: 债务/收入/消费/投资/房产/交易
   方向: 目标/底线/规则/决策/复盘/正向循环
4. related_topics(相关主题,0-2 个数组):只能从上述固定主题中选择,不能与 main_topic 重复。
5. tags(标签,0-5 个数组):少量具体关键词,如 ["专注达","反跳","他人经验"]。
   他人经验/医生建议/官方说明属于标签,不是来源。不要生成同义重复词。
6. highlights(重点原句,0-3 个数组):逐字复制输入中最有价值的完整句子,不能改写、补充或总结;
   没有明显重点时返回空数组。

不允许新增类型、领域或主题。不要输出 use_tag/topics/source。
输出:{"entry_type":"知识","domain":"身心","main_topic":"药物","related_topics":["ADHD"],"tags":["专注达","他人经验"],"highlights":["原文中的完整句子"]}"""


def parse_json(text: str) -> dict:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?", "", t).strip()
        t = re.sub(r"```$", "", t).strip()
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e != -1 and e > s:
        t = t[s:e + 1]
    return json.loads(t)


def normalize(raw: dict) -> dict:
    et = (raw.get("entry_type") or "").strip()
    dm = (raw.get("domain") or "").strip()
    mt = (raw.get("main_topic") or "").strip()
    related = raw.get("related_topics") or []
    if not isinstance(related, list):
        related = []
    allowed_related = []
    for value in related:
        topic = str(value).strip()
        if topic in FIXED_TOPICS and topic != mt and topic not in allowed_related:
            allowed_related.append(topic)
    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tags = list(dict.fromkeys(str(t).strip() for t in tags if str(t).strip()))[:5]
    highlights = raw.get("highlights") or []
    if not isinstance(highlights, list):
        highlights = []
    highlights = [str(t).strip() for t in highlights if str(t).strip()][:3]
    return {
        "entry_type": et if et in ENTRY_TYPES else None,
        "domain": dm if dm in DOMAINS else None,
        "main_topic": mt if mt in TOPICS_BY_DOMAIN.get(dm, []) else None,
        "related_topics": allowed_related[:2] or None,
        "tags": tags or None,
        "highlights": highlights or None,
    }


async def call_classify(body: str, model: str | None = None) -> dict:
    """给一段文字打固定分类。失败抛异常。"""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY 未配置")
    payload = {
        "model": model or VISION_MODEL,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": (body or "")[:2000]},
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "zbrain",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        body_json = resp.json()
    content = body_json["choices"][0]["message"]["content"]
    out = normalize(parse_json(content))
    out["_raw"] = content
    return out
