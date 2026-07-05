"""AI 自动分类:给文字条目(core.entries)打统一 5 维度里的 4 个(source 已在写入时定)。

枚举严格固定(见 models/entries.py 的 Literal);prompt 把固定值+含义全给模型,只能选里面的,
后端再 normalize 校验一遍,非法值置空,不污染数据。topics 自由生成。
"""
import json
import re

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, VISION_MODEL

ENTRY_TYPES = {"想法", "句子", "规则", "决策", "知识", "资料", "记录"}
DOMAINS = {"身心", "生活", "能力", "财务", "方向"}
USE_TAGS = {"方法", "避坑", "心态", "工具", "灵感", "存档", "决策", "参考"}

PROMPT = """你是一个个人第二脑的内容分类器。给你一段用户自己写的文字,请按固定分类打标。
只返回一个 JSON 对象,不要解释、不要 markdown 包裹。

1. entry_type(类型,择一):
   想法=我的理解/判断/感悟  句子=认可并想保存的一句话  规则=以后要执行的行为准则
   决策=已经确定的选择  知识=可学习可复用的信息  资料=合同/证件/药盒/票据/配置等材料
   记录=当时发生的事/状态/情绪/体验/时间线
2. domain(领域,择一):
   身心=情绪/ADHD/药物/运动/睡眠/身体/健康  生活=马德里/居住/合同/证件/家庭/日常/办事
   能力=西班牙语/AI/编程/项目/服务器/学习/写作  财务=债务/收入/消费/投资/房产/交易/风控/养老金
   方向=目标/底线/规则/长期规划/正向循环/人生策略
3. use_tag(用途,择一):
   方法=可以照着做  避坑=防止犯错  心态=稳定情绪和认知  工具=软件/网站/脚本/系统
   灵感=有启发未来可能发展  存档=需要留存的东西  决策=支撑或记录一个选择  参考=以后可能查/对照
4. topics(标签,自由关键词,2-5 个数组):具体讲什么,如 ["ADHD","药物","专注达"];
   别人经历一律加 "他人经验"。
5. highlights(重点原句,0-3 个数组):逐字复制输入中最有价值的完整句子,不能改写、补充或总结;
   没有明显重点时返回空数组。

必须从上面 1-3 的固定值里选;拿不准就选最接近的。
输出:{"entry_type":"想法","domain":"身心","use_tag":"心态","topics":["ADHD"],"highlights":["原文中的完整句子"]}"""


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
    ut = (raw.get("use_tag") or "").strip()
    topics = raw.get("topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [str(t).strip() for t in topics if str(t).strip()][:5]
    highlights = raw.get("highlights") or []
    if not isinstance(highlights, list):
        highlights = []
    highlights = [str(t).strip() for t in highlights if str(t).strip()][:3]
    return {
        "entry_type": et if et in ENTRY_TYPES else None,
        "domain": dm if dm in DOMAINS else None,
        "use_tag": ut if ut in USE_TAGS else None,
        "topics": topics or None,
        "highlights": highlights or None,
    }


async def call_classify(body: str, model: str | None = None) -> dict:
    """给一段文字打分类。返回规整后的 4 维 dict。失败抛异常。"""
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
