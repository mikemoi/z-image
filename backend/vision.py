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
   asset     —— 证件/票据/二维码/序列号/地址/账号密码/保修卡等"要用时查出来"的资料凭证,
                不是用来消化沉淀的知识。识别到这类一律 asset。
5. summary:一句话说清"这张图讲了什么"。
   对图解/K线/形态/手绘/白板等无正文的图,描述其表达的方法或结构
   (例:"葛兰威尔均线八大买卖点示意图"),这是唯一检索抓手。
   fragment 类,summary 可等于那句话本身。
   asset 类,summary 说清"这是什么资料/证件"(例:"XX 的身份证正面"、"XX 保险保单"),
   便于日后检索,注意不要照抄敏感号码到 summary。
6. is_ocr_suitable:图片主体是否为「值得入库的正文文字」。
   true:文章/回答/笔记/评论正文。
   false:K线图/形态图/手绘/白板拍照/表情包/纯图/无信息量评论流("写得真好")/纯一句金句。
7. 若 is_ocr_suitable=true,提取 ocr_text:
   只提主体正文。必须忽略:顶部状态栏(时间/电量/信号)、平台UI(用户名/头像/时间地点/
   点赞收藏评论转发数/关注按钮/搜索框/下载广告)、背景照片上文字、相册底部缩略图条、
   无信息量礼貌性评论。保留正文原文,不改写。
   若 false,ocr_text 省略或空。
8. suggested_theme:第 2 项 theme 只能从固定六类挑,其中 life 和 other 是"兜底大类"。
   如果这张图能归到一个更具体的领域(如运动/健身、情绪、健康、旅行、育儿、美食、职场等),
   哪怕勉强能塞进 life/other,也在这里给出那个更具体的中文名(如"运动");
   若它本就贴合 trading/ai/adhd/language、或确实没有更具体的领域可归,留空字符串。不要滥造。
9. quality:对信息价值判断,择一。**"鸡汤"不等于没用,别一刀切**:
   "干货" —— 有方法/论证/信息量,值得留。
   "反面样本" —— 情绪帖/踩坑/爆仓/普遍误区,像鸡汤但有"避坑"借鉴价值,值得留。
   "无信息量" —— 纯灌水、纯礼貌评论("写得真好")、无提炼价值,可考虑清理。只有真的什么都没剩才判它。

输出:{"title":"","theme":"life","use":"心态","granularity":"fragment","summary":"...","is_ocr_suitable":false,"suggested_theme":"","quality":"干货"}

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
_GRANS = {"knowledge", "fragment", "asset"}


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
    # 新分类候选:六类之一(含大小写)则视为无候选,不硬造重复
    st = (raw.get("suggested_theme") or "").strip()
    if st.lower() in _THEMES:
        st = ""
    q = (raw.get("quality") or "").strip()
    return {
        "title": (raw.get("title") or "").strip() or None,
        "theme": theme if theme in _THEMES else "other",
        "use_tag": use if use in _USES else None,
        "granularity": gran if gran in _GRANS else "fragment",
        "summary": (raw.get("summary") or "").strip() or None,
        "is_ocr_suitable": bool(raw.get("is_ocr_suitable", False)),
        "ocr_text": (raw.get("ocr_text") or "").strip() or None,
        "suggested_theme": st or None,
        "quality": q if q in _QUALITY else None,
    }


async def _chat_image(prompt: str, file_path: str, model: str | None = None,
                      temperature: float = 0.0) -> str:
    """把 prompt + 原图发给 OpenRouter,返回模型文本。model 缺省用 VISION_MODEL。任何失败抛异常。"""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY 未配置")

    data = Path(file_path).read_bytes()
    b64 = base64.b64encode(data).decode()
    data_uri = f"data:{_mime_for(file_path)};base64,{b64}"

    payload = {
        "model": model or VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ],
        }],
        "temperature": temperature,
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

    return body["choices"][0]["message"]["content"]


async def call_vision(file_path: str, model: str | None = None) -> dict:
    """把原图发给 OpenRouter(自动处理),返回规整后的 dict。任何失败抛异常。"""
    content = await _chat_image(PROMPT, file_path, model=model, temperature=0)
    parsed = normalize(parse_json(content))
    parsed["_raw_content"] = content  # 存进 ai_output 备查
    return parsed


# ── 「问问 AI」:按需生成的看法 / 定义 / 质量判断 / 分类建议 ────────────────────
# 红线:这是 AI 补充,不是原文;鸡汤≠该删——情绪帖/踩坑有"避坑"价值,只有纯无信息量才建议清。
INSIGHT_PROMPT = """你是用户第二脑里的讲解员。用户存了一张图/一段内容,现在主动点开、想听你的看法。
已知信息:
{context}

只返回一个 JSON 对象,不要任何解释、不要 markdown 包裹。

1. explanation:把这张图/这段内容讲明白——它在讲什么、关键术语什么意思、你的一句看法。
   像一个懂行的朋友三两句点透,别复述原文。100-200 字。
2. quality:对信息价值的判断,择一:
   "干货" —— 有方法/论证/信息量,值得留。
   "反面样本" —— 情绪帖/踩坑/爆仓/普遍误区,本身像鸡汤,但用户可借以反思规避,有"避坑"价值,值得留。
   "无信息量" —— 纯灌水、纯礼貌性评论("写得真好")、无提炼价值,可考虑清理。
   注意:不要把有反面价值的内容误判成"无信息量";只有真的什么都没剩下才判"无信息量"。
3. quality_note:一句话说明为什么这么判断(尤其"反面样本"要说清它的借鉴价值在哪)。
4. suggested_theme:现有主题分类有:{themes}。
   如果这条内容明显不属于其中任何一个、需要一个新分类,给出新分类的简短中文名(如"运动""情绪""健康");
   如果现有分类里有能装下它的,留空字符串,不要硬造。
5. suggested_theme_reason:若提议了新分类,一句话说为什么;否则留空。

输出示例:{{"explanation":"...","quality":"干货","quality_note":"...","suggested_theme":"","suggested_theme_reason":""}}"""

_QUALITY = {"干货", "反面样本", "无信息量"}


def normalize_insight(raw: dict) -> dict:
    q = (raw.get("quality") or "").strip()
    st = (raw.get("suggested_theme") or "").strip()
    return {
        "explanation": (raw.get("explanation") or "").strip(),
        "quality": q if q in _QUALITY else None,
        "quality_note": (raw.get("quality_note") or "").strip() or None,
        "suggested_theme": st or None,
        "suggested_theme_reason": (raw.get("suggested_theme_reason") or "").strip() or None,
    }


async def call_insight(file_path: str, context: dict, existing_themes: list[str],
                       model: str | None = None) -> dict:
    """按需生成看法。context: {title, summary, clean_text};existing_themes: 现有主题名列表。"""
    lines = []
    if context.get("title"):
        lines.append(f"标题:{context['title']}")
    if context.get("summary"):
        lines.append(f"摘要:{context['summary']}")
    if context.get("clean_text"):
        lines.append(f"正文:{context['clean_text'][:2000]}")
    ctx = "\n".join(lines) or "(没有已提取的文字,主要看图判断)"
    prompt = INSIGHT_PROMPT.format(context=ctx, themes="、".join(existing_themes) or "(无)")
    content = await _chat_image(prompt, file_path, model=model, temperature=0.3)
    return normalize_insight(parse_json(content))
