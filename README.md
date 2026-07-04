# zbrain · 第二脑

> 自托管、单用户的综合存储库 —— 你所有的碎片、截图、笔记数字化进来,方便你在需要时用。
> **z-image** 是第一个入口,聚焦手机截图。

**唯一准绳:** "方便我用" 压倒 "存得全"。三条气质贯穿始终:

- **anti-anxiety** —— 无 streak、无待办计数、无焦虑指标;删除无劝阻无愧疚。
- **self-use** —— 成功标准是"我真的天天用它、手机真的清空了",不是完备度。
- **别变成整理花园** —— 自动流水线优先,不逼用户手动经营结构。

---

## 功能全貌

### 进(数字化)· 清空节奏
- **批量上传,上传即走**:手机相册多选 → 秒回"✓ 已接收 N 张,手机可清空" → 立刻删手机原图。绝不显示"N 张待处理",不制造待办焦虑。
- **原图落盘 + checksum 去重**:sha256 命名存 `/data/zbrain/files/`,同图只存一份。
- **原图是唯一副本**:删手机后磁盘原图即事实源,需单独备份。

### 消化节奏 · 后台 AI(无时间压力)
- **一次 Vision 调用**自动判定:`title / theme / use / granularity / summary / is_ocr_suitable`。
- **两段式省钱**:先判"适不适合入库正文",只对适合的做 OCR;图解/K线/手绘只存一句 summary(唯一检索抓手)。
- **机械清洗兜底**:剥离状态栏、平台 UI(点赞/关注/评论)、纯 URL 等残留噪音。
- **稳健运行**:每日预算上限、失败自动重试到上限、可续跑;任何失败不阻塞,停在 `review` 等人工兜底。

### 用(方便用)· 四种遇见
- **按维度浏览**:主题 × 用途交叉筛选。主题**可生长**——AI 遇到装不下的领域(运动/情绪…)会攒够一簇后建议新建,你点头才加(用途保持稳定五类)。
- **重新遇见**:首页偶尔翻出最久没见的碎片,配原图缩略,看完轮换。无待办、纯偶遇。
- **搜索**:全文检索**全部内容**(截图条目 + 手写文字,标题/摘要/正文,中文走子串兜底)。
- **关联**:预留 pgvector(第二刀)。

### 问问 AI · 会给你讲的第二脑(v0.3)
- **详情页「问问 AI」**:你主动点才调用(拉不推、按需付费),结果缓存不重复烧钱。
- 给三样:**看法/定义**(讲明白这是什么,标「AI 补充」与原文分开)、**质量判断**(干货/反面样本/无信息量)、**新分类建议**(一键采纳)。

### 记 · 文字入口(v0.3)
- **速记 / 日志 / 计划 / AI 剪藏**,零摩擦记下(`core.entries`,复用 core)。
- **速记/剪藏** → 待整理 → 归位进精选脑或碎片箱;**日志** → 带日期、按天翻、往年今天、可选心情(绝不 streak);**计划** → 钉住常驻。

### 消化闭环 · 三层存储门槛递减
```
image.contents.clean_text
  ├─ knowledge → ①review(标记已看)→ ②promote(手动入脑)→ core.knowledge(切块 + 打 theme/use 标签)
  └─ fragment  → ①review 确认是碎片 → core.notes(轻路径,无第二道闸门)
```

### 删(提纯)· 删除三档 + 清库
- **删除**(一键软删,无劝阻):任何界面看到"什么玩意"立即消失,原文件与记录仍在。日常唯一常用。
- **回收站**(后悔药):软删项可恢复。
- **彻底销毁**(二次确认):永久抹磁盘原文件 + 删记录,共享文件被引用时不误删。
- **清库(v0.3)**:AI 自动处理时顺手判「无信息量」,你主动进「清库」才聚合列出、一眼扫着删——不推送、不计数(鸡汤≠该删,只出纯无信息量的)。

---

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | FastAPI(Python 3.12) |
| 数据库 | PostgreSQL 17(库名 `zbrain`,schema:`core` + `image`) |
| 前端 | React + Vite + PWA(按 iPhone 竖屏优化,可加主屏) |
| AI | OpenRouter Vision(`openai/gpt-4.1-mini`) |
| 部署 | Docker Compose(单容器全栈 + 自带 PG) |

**向量现在不做**,预留 pgvector 注释;Qdrant 对单人自托管是纯负债。

---

## 目录结构

```
z-image/
├── backend/               FastAPI 后端
│   ├── main.py            入口:健康检查 + 挂载前端 dist + 后台 worker + 启动迁移
│   ├── db.py              PostgreSQL 连接池 + ensure_schema() 运行时迁移
│   ├── auth.py            单用户 header token 鉴权
│   ├── config.py          环境变量
│   ├── vision.py          OpenRouter:自动分析(call_vision)+ 问问AI(call_insight)
│   ├── worker.py          后台轮询处理 + 每日预算 + 失败重试
│   ├── clean.py           机械清洗
│   ├── routers/           items / files / stats / feed / search / entries
│   └── models/            items / entries(Pydantic 模型)
├── frontend/              React + Vite + PWA
│   └── src/
│       ├── pages/         Upload / Home / Browse / Detail / Trash / Search
│       │                  Capture / Inbox / Logs / Cleanup(文字入口 + 清库)
│       └── components/    TabBar / Icon(线性图标) / Img / ItemCard / TokenGate
├── docs/                  📖 详细文档(设计参考)
│   ├── DATABASE.md        数据字典:每表每字段含义 + 枚举 + JSONB 结构
│   ├── API.md             完整端点参考
│   └── CHANGELOG.md       版本变更历史
├── deploy/
│   ├── init.sql           建表脚本(幂等)
│   └── README.md          部署速查
├── zbrain-architecture-v3.md   架构蓝图(what/why + schema + Vision prompt)
├── v0.3-plan.md           下一步规划(向量/存量/文字入口重构/计划体系)
├── Dockerfile            多阶段:构建前端 + 后端服务
├── docker-compose.yml    postgres + backend 一键起
└── .env.example          服务器配置模板
```

> **详细的数据库结构、字段含义、API、版本变化**见 [`docs/`](docs/) 目录——以后设计时先看那里。

---

## API

所有 `/api/*` 除 `/api/health` 外均需鉴权:`Authorization: Bearer <AUTH_TOKEN>`。

分组概览(**完整端点、参数、返回见 [`docs/API.md`](docs/API.md)**):

| 分组 | 前缀 | 主要能力 |
|---|---|---|
| 条目 | `/api/items` | 上传 / 列表 / 详情 / 改标签 / 问问AI / 采纳分类 / 清库 / review·promote·落箱 / 软删·恢复·销毁 |
| 文字入口 | `/api/entries` | 记一条 / 待整理 / 计划 / 日志·往年今天 / 归位 / 软删·恢复 |
| 维度·生长分类 | `/api/stats` | 维度计数 / 新分类候选 / 批量采纳 |
| 搜索 | `/api/search` | 全文检索(截图 + 手写文字) |
| 重新遇见 | `/api/feed` | 取碎片 / 删碎片 |
| 原图 | `/api/files` | 按 checksum 取原图 |
| 系统 | — | `/api/health` `/api/whoami` `/api/worker/status` |

在线交互文档:`http://<host>:8000/docs`。

---

## 本地开发

前提:PostgreSQL 已装、库 `zbrain` 已建(见下方建库),Python 3.12、Node。

```powershell
# 1. 建库(首次)
psql -U postgres -c "CREATE DATABASE zbrain;"
psql -U postgres -d zbrain -f deploy/init.sql

# 2. 后端
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env      # 填 DATABASE_URL / AUTH_TOKEN / OPENROUTER_API_KEY
.\.venv\Scripts\python.exe -m uvicorn main:app --reload

# 3. 前端(另开一个终端)
cd frontend
npm install
npm run dev                 # host 已开,同 WiFi 手机可用 http://<局域网IP>:5173
```

或项目根目录一键起:`./start-dev.ps1`。

前端 API 文档:`http://127.0.0.1:8000/docs`。前端口令门预填 `dev-token-change-me`。

---

## 上服务器部署(中文指南)

单容器全栈(前端 dist 打进后端镜像,单端口 8000)+ 自带 PostgreSQL(首次启动自动建库)。服务器需装好 Docker 与 Docker Compose。

### 1. 拉代码

```bash
git clone https://github.com/mikemoi/z-image.git
cd z-image
```

### 2. 配置密钥

```bash
cp .env.example .env
```

编辑 `.env`,**务必改掉这三项**:

```ini
POSTGRES_PASSWORD=改成强密码
AUTH_TOKEN=改成随机长串           # 前端登录口令用它
OPENROUTER_API_KEY=sk-or-v1-...   # 你的 OpenRouter key
VISION_DAILY_BUDGET=500           # 每日 Vision 调用上限,按额度调
```

### 3. 一键启动

```bash
docker compose up -d --build
```

Compose 会:
1. 起 `postgres:17`,**首次**启动自动执行 `deploy/init.sql` 建好全部表 + 预置标签;
2. 构建镜像(node 构建前端 dist → python 后端挂载它);
3. 等 DB healthcheck 通过后再起后端。

### 4. 访问

浏览器开 `http://<服务器IP>:8000`,口令填 `.env` 里的 `AUTH_TOKEN`。iPhone 上 Safari 打开后可"添加到主屏幕"变 PWA。

### 5. 生产建议

- **HTTPS / 反向代理**:前面挂 Nginx(1Panel)反代到 `:8000`,配好证书。`upload/delete` 不要裸奔公网。
- **原图备份(重要)**:原图落宿主机 `/data/zbrain/files`,用户删手机后是**唯一副本**——配定期备份,磁盘挂 = 图没了。
- **已有外部 PG**:删掉 compose 里的 `db` 服务,把 backend 的 `DATABASE_URL` 指向你的 PG,并先手动 `psql -d zbrain -f deploy/init.sql`。

### 更新与运维

```bash
git pull && docker compose up -d --build   # 更新
docker compose logs -f backend             # 看后端日志
docker compose down                        # 停(数据卷 pgdata 保留)
```

### 存量导入提醒

历史 5-6000 张图**不要初期一次性灌**。先用系统消化"每天约 50 张新增"、养成习惯,再把存量作为独立的限速慢跑任务分批处理(否则淹没在待 review 里,违背 anti-anxiety)。

---

## 文档索引

**北极星(方向模糊、功能膨胀时先看这个)**
- [`docs/FRAMEWORK.md`](docs/FRAMEWORK.md) —— 产品本质与板块蓝图:这软件到底是什么、每个板块为什么存在、主循环、带偏自查

**设计参考(以后设计先看这里)**
- [`docs/DATABASE.md`](docs/DATABASE.md) —— 数据字典:每表每字段含义、枚举值、JSONB 结构、关系
- [`docs/API.md`](docs/API.md) —— 完整 API 端点参考
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) —— 每个版本的详细变化

**蓝图与规划**
- `zbrain-architecture-v3.md` —— 架构蓝图(what/why、完整 schema、Vision prompt)
- `zbrain-claude-code-buildbook.md` —— 五步施工手册(how)
- [`v0.3-plan.md`](v0.3-plan.md) —— 下一步规划(向量语义聚合 / 存量导入 / 文字入口时间流重构 / 计划体系)

**进度**:v0.1 五步 MVP(能存)→ v0.2 部署 + 体验(能部署)→ **v0.3 智能整理 + 文字入口 + 视觉升级(会整理·当前)**。详见 CHANGELOG。
