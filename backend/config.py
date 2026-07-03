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

# OpenRouter(第三步用,先占位)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "openai/gpt-4.1-mini")

# 每日 Vision 调用预算(第三步用)
VISION_DAILY_BUDGET = int(os.getenv("VISION_DAILY_BUDGET", "500"))
