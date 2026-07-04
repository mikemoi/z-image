"""集中读取环境变量。单用户,配置极简。"""
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库连接串,例:postgresql://postgres:pass@localhost:5432/zbrain
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:zbrain2024@localhost:5432/zbrain")

# 单用户鉴权 token,前端每次请求带在 header
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "dev-token-change-me")

# 原文件磁盘根目录(第二步用)
FILES_ROOT = os.getenv("FILES_ROOT", "./data/zbrain/files")

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
VISION_MODEL = os.getenv("VISION_MODEL", "openai/gpt-4.1-mini")
# 问问 AI 用的模型(默认同 OCR,建议在「我的」里换更强的:低频+缓存,成本可控、质量值)
INSIGHT_MODEL = os.getenv("INSIGHT_MODEL", VISION_MODEL)

# 每日 Vision 调用预算。0 或负数 = 不限制(交给 OpenRouter/API 侧限流)。
VISION_DAILY_BUDGET = int(os.getenv("VISION_DAILY_BUDGET", "0"))

# 单个 item 自动重试上限,超过停在 review 等人工兜底
VISION_MAX_ATTEMPTS = int(os.getenv("VISION_MAX_ATTEMPTS", "3"))

# 后台 worker 轮询间隔(秒)
WORKER_POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "8"))
