# 单容器全栈:构建前端 dist,后端(FastAPI)同端口挂载它。
# 用法:docker compose up -d --build

# ── stage 1:构建前端 ─────────────────────────────────────────────────────────
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # 产出 /fe/dist

# ── stage 2:后端 + 前端 dist ─────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
# main.py 找 ../frontend/dist,放到 /app/frontend/dist
COPY --from=frontend /fe/dist ./frontend/dist

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
