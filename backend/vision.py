"""OpenRouter Vision 调用 + 强制 JSON 解析。prompt 来自 architecture-v3 §6。"""
import re
import json
import base64
from pathlib import Path

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, VISION_MODEL

# ── §6 完整 prompt(强制 JSON) ───────────────────────────────────────────────
PROMPT = """你是一个个人第二脑的图片分析器。用户给你一张手机截图或图片。
只返回一个 JSON 对象,不要任何解释、不要 markdown 包裹。

1. title:如果图中有明确的原文标题/问题/主标(如知乎问题、文章标题),原样提取;没有则空字符串。
2. theme(主题,择一):trading / ai / adhd / language / life / other
3. use(用途,用户最可能拿它做什么,择一):
   方法(讲怎么做的体系知识/步骤/系统)、
   避坑(别人踩的坑/失败/爆仓/普遍误区,用户借以反思规避)、
   心态(该保持的状态/情绪调节/认知态度)、
   工具(具体软件/项目/资源)、灵感(触发思考的点子/观点)
4. granularity(粒度,择一):
   knowledge —— 成体系、有信息量、能独立成立的知识(方法/论证/清单/架构)
   fragment  —— 一句孤立的感悟/金句/万金油提醒(去掉它只损失"一句提醒")
5. summary:一句话说清"这张图讲了什么"。
   对图解/K线/形态/手绘/白板等无正文的图,描述其表达的方法或结构
   (例:"葛兰威尔均线八大买卖点示意图"),这是唯一检索抓手。
   fragment 类,summary 可等于那句话本身。
6. is_ocr_suitable:图片主体是否为「值得入库的正文文字」。
   true:文章/回答/笔记/评论正文。
   false:K线图/形态图/手绘/白板拍照/表情包/纯图/无信息量评论流("写得真好")/纯一句金句。
7. 若 is_ocr_suitable=true,提取 ocr_text:
   只提主体正文。必须忽略:顶部状态栏(时间/电量/信号)、平台UI(用户名/头像/时间地点/
   点赞收藏评论转发数/关注按钮/搜索框/下载广告)、背景照片上文字、相册底部缩略图条、
   无信息量礼貌性评论。保留正文原文,不改写。
   若 false,ocr_text 省略或空。

输出:{"title":"","theme":"life","use":"心态","granularity":"fragment","summary":"...","is_ocr_suitable":false}

边界:
- 交易内容:主体在讲"怎么做/为什么/别人栽哪"就归对应 use;拿不准偏"方法",最终入脑用户手动把关。
- 纯情绪宣泄或纯无信息量评论:theme 照填,is_ocr_suitable=false。
- granularity 拿不准时偏 fragment(碎片进 notes 无闸门,更轻;误判损失小)。"""

_MIME = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "gif": "image/gif",
}

_THEMES = {"trading", "ai", "adhd", "language", "life", "other"}
_USES = {"方法", "避坑", "心态", "工具", "灵感"}
_GRANS = {"knowledge", "fragment"}


def _mime_for(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    return _MIME.get(ext, "image/jpeg")


def parse_json(text: str) -> dict:
    """稳健解析:剥离 ```json 围栏、取第一个 {} 块。失败则抛。"""
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?", "", t).strip()
        t = re.sub(r"```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start:end + 1]
    return json.loads(t)


def normalize(raw: dict) -> dict:
    """把模型输出规整成库内字段,兜底非法枚举值。"""
    theme = (raw.get("theme") or "").strip().lower()
    use = (raw.get("use") or "").strip()
    gran = (raw.get("granularity") or "").strip().lower()
    return {
        "title": (raw.get("title") or "").strip() or None,
        "theme": theme if theme in _THEMES else "other",
        "use_tag": use if use in _USES else None,
        "granularity": gran if gran in _GRANS else "fragment",
        "summary": (raw.get("summary") or "").strip() or None,
        "is_ocr_suitable": bool(raw.get("is_ocr_suitable", False)),
        "ocr_text": (raw.get("ocr_text") or "").strip() or None,
    }


async def call_vision(file_path: str) -> dict:
    """把原图发给 OpenRouter,返回规整后的 dict。任何失败抛异常。"""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY 未配置")

    data = Path(file_path).read_bytes()
    b64 = base64.b64encode(data).decode()
    data_uri = f"data:{_mime_for(file_path)};base64,{b64}"

    payload = {
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ],
        }],
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
        body = resp.json()

    content = body["choices"][0]["message"]["content"]
    parsed = normalize(parse_json(content))
    parsed["_raw_content"] = content  # 存进 ai_output 备查
    return parsed
