"""AI 自动分类:类型 + 领域 + 主题 + 子题 + 关联 + 少量标签(source 由入口确定)。

枚举严格固定(见 models/entries.py 的 Literal);prompt 把固定值+含义全给模型,只能选里面的,
后端再 normalize 校验一遍；AI 只能归类，不能扩建固定体系。
"""
import json
import re

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, VISION_MODEL
from classification_schema import (
    DOMAINS, ENTRY_TYPES, FIXED_TOPICS, SUB_TOPICS_BY_TOPIC, TOPICS_BY_DOMAIN,
    normalize_entry_type, normalize_sub_topic,
)

PROMPT = """你是一个个人第二脑的内容分类器。给你一段文字,请按固定体系归类。
只返回一个 JSON 对象,不要解释、不要 markdown 包裹。

1. entry_type(类型,择一):
   想法=我的理解/判断/感悟/句子/认知沉淀  知识=外部经验/教程/解释/可学习内容
   资料=合同/证件/药盒/票据/配置等要留存的材料  记录=当时发生的事/状态/情绪/体验/时间线
   规则=底线/决策/行为准则/不做清单
2. domain(领域,择一):
   身心=情绪/ADHD/药物/运动/睡眠/身体/健康  生活=马德里/居住/合同/证件/家庭/日常/办事
   能力=西班牙语/AI/编程/项目/服务器/学习/写作  财务=债务/收入/消费/投资/房产/交易/风控/养老金
   方向=目标/底线/规则/长期规划/正向循环/人生策略
3. main_topic(主题,择一且必须属于所选领域):
   身心: ADHD/情绪/药物/运动/睡眠/身体
   生活: 马德里/居住/证件/合同/关系/日常
   能力: 西班牙语/AI/编程/服务器/产品/学习
   财务: 债务/收入/消费/投资/房产/交易
   方向: 目标/底线/规则/决策/复盘/正向循环
4. sub_topic(子题,择一且必须属于 main_topic):从固定子题表选择。
   如果固定子题不够准确，不要强塞到错误子题，返回"未细分"，并在 candidate_sub_topic 提名候选。
   固定子题表:
   __SUB_TOPICS__
5. related_topics(相关,0-2 个数组):只能从上述固定主题中选择,不能与主题重复。
6. tags(标签,0-5 个数组):少量具体关键词,优先用稳定标签,如 ["专注达","反跳","他人经验"]。
   他人经验/医生建议/官方说明属于标签,不是来源。不要生成同义重复词。
7. candidate_tags(候选标签,0-5 个数组):正式标签不够时提出候选,不能直接当正式体系。
8. candidate_sub_topic:固定子题不够时提出候选子题,否则 null。候选子题不是正式子题。
   candidate_sub_topic_domain / candidate_sub_topic_main_topic:候选子题建议放置的位置。

不允许新增类型、领域、主题、正式子题或来源。不要输出 use_tag/topics/source/highlights。
输出:{"entry_type":"知识","domain":"身心","main_topic":"药物","sub_topic":"专注达","related_topics":["ADHD"],"tags":["反跳","他人经验"],"candidate_tags":[],"candidate_sub_topic":null,"candidate_sub_topic_domain":null,"candidate_sub_topic_main_topic":null}"""

PROMPT = PROMPT.replace(
    "__SUB_TOPICS__",
    "\n   ".join(f"{topic}: {'/'.join(values)}" for topic, values in SUB_TOPICS_BY_TOPIC.items()),
)


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
    et = normalize_entry_type(raw.get("entry_type"))
    dm = (raw.get("domain") or "").strip()
    mt = (raw.get("main_topic") or "").strip()
    sub = normalize_sub_topic(mt, raw.get("sub_topic"))
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
    candidate_tags = raw.get("candidate_tags") or []
    if not isinstance(candidate_tags, list):
        candidate_tags = []
    candidate_tags = list(dict.fromkeys(str(t).strip() for t in candidate_tags if str(t).strip()))[:5]
    candidate_sub_topic = (raw.get("candidate_sub_topic") or "").strip() or None
    candidate_sub_topic_domain = (raw.get("candidate_sub_topic_domain") or "").strip() or None
    candidate_sub_topic_main_topic = (raw.get("candidate_sub_topic_main_topic") or "").strip() or None
    if candidate_sub_topic_domain not in DOMAINS:
        candidate_sub_topic_domain = None
    if candidate_sub_topic_main_topic not in FIXED_TOPICS:
        candidate_sub_topic_main_topic = None
    return {
        "entry_type": et,
        "domain": dm if dm in DOMAINS else None,
        "main_topic": mt if mt in TOPICS_BY_DOMAIN.get(dm, []) else None,
        "sub_topic": sub if mt in TOPICS_BY_DOMAIN.get(dm, []) else None,
        "related_topics": allowed_related[:2] or None,
        "tags": tags or None,
        "candidate_tags": candidate_tags or None,
        "candidate_sub_topic": candidate_sub_topic,
        "candidate_sub_topic_domain": candidate_sub_topic_domain,
        "candidate_sub_topic_main_topic": candidate_sub_topic_main_topic,
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
