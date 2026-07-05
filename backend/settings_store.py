"""运行时设置读写(core.settings kv)。当前用于 OCR / 问问AI 模型切换。

模型解析优先级:core.settings 里的值 > 环境变量默认(config)。
所以「我的」里改了就即时生效,没改则用 .env 的默认,不用重启。
"""
from db import get_conn
from config import VISION_MODEL, INSIGHT_MODEL

# 预置候选(方便下拉;非限制,前端可自定义输入任意 OpenRouter 模型 id)。
# OCR/自动处理偏省钱档,问问AI 偏质量档,两者都需支持读图(vision)。
MODEL_CANDIDATES = {
    "ocr_model": [
        "openai/gpt-4.1-mini",
        "openai/gpt-4o-mini",
        "google/gemini-2.0-flash-001",
    ],
    "insight_model": [
        "openai/gpt-4.1",
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-pro",
        "openai/gpt-4o",
    ],
    "classify_model": [
        "openai/gpt-4.1-mini",
        "openai/gpt-4o-mini",
        "google/gemini-2.0-flash-001",
    ],
}

_DEFAULTS = {"ocr_model": VISION_MODEL, "insight_model": INSIGHT_MODEL, "classify_model": VISION_MODEL}


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM core.settings WHERE key = %s", (key,)
        ).fetchone()
    return row["value"] if row and row["value"] else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO core.settings (key, value, updated_at) VALUES (%s, %s, now())
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()""",
            (key, value),
        )
        conn.commit()


def ocr_model() -> str:
    return get_setting("ocr_model", _DEFAULTS["ocr_model"])


def insight_model() -> str:
    return get_setting("insight_model", _DEFAULTS["insight_model"])


def classify_model() -> str:
    return get_setting("classify_model", _DEFAULTS["classify_model"])


def current_models() -> dict:
    return {"ocr_model": ocr_model(), "insight_model": insight_model(),
            "classify_model": classify_model()}
