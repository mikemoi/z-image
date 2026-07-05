# 项目交接文档 · zbrain / z-image

> 写给下一个接手的工程师。目标:读完这份 + `docs/` 其余几份,就能独立继续开发、部署、排障。
> 深度细节分散在:[FRAMEWORK.md](FRAMEWORK.md)(产品北极星)、[STATUS.md](STATUS.md)(现状快照)、[BLOCKS.md](BLOCKS.md)(板块施工)、[DATABASE.md](DATABASE.md)(数据字典)、[API.md](API.md)、[CHANGELOG.md](CHANGELOG.md)。本文件是总入口。

---

## 0. 一句话:这是什么

不是存储/笔记软件,是**"对抗遗忘、把你截图刷到的东西持续变成你思考"的复利机器**。
主循环:**捕捉 → 后台消化 → 重新遇见 → 追问 → 想法 → 精选**,检索/提纯贯穿。
三条准绳:anti-anxiety(无待办无计数)、self-use(真天天用)、别做整理花园(自动优先,不逼手动经营)。
单用户、自托管。设计者本人是唯一用户,在马德里,ADHD,内容含交易/西语/AI/编程/身心健康等。

---

## 1. 技术栈与仓库

- **后端**:FastAPI(Python 3.12)+ PostgreSQL 17(schema `core` + `image`)。
- **前端**:React + Vite + PWA(iPhone 竖屏优先)。
- **AI**:OpenRouter(chat completions)。默认 `openai/gpt-4.1-mini`。
- **部署**:单容器(前端 dist 打进后端镜像,单端口 8000)+ 自带 Postgres。Docker Compose。
- **仓库**:GitHub `mikemoi/z-image`,分支 `main`。git 身份 `zbrain <momol.gz@gmail.com>`(本地 `git config` 设的,非 global)。

### 目录结构
```
backend/
  main.py         入口:lifespan(open_pool → ensure_schema → start_worker)+ 挂载前端 dist
  config.py       环境变量(DATABASE_URL/AUTH_TOKEN/OPENROUTER_*/VISION_MODEL/INSIGHT_MODEL/VISION_DAILY_BUDGET…)
  db.py           连接池 + ensure_schema()(运行时幂等迁移)
  auth.py         单用户 Bearer token 鉴权
  vision.py       call_vision(截图自动分析)+ call_insight(问问AI)+ _chat_image
  classify.py     call_classify(文字/截图 5 维分类)+ 固定枚举 prompt + normalize 校验
  clean.py        OCR 文本机械清洗
  worker.py       两个后台循环:_loop(Vision)+ _classify_loop(分类);预算 0=不限
  settings_store.py  core.settings kv:ocr_model/insight_model/classify_model 运行时切换
  routers/        items / entries / stats / search / feed / files / settings
  models/         items.py / entries.py(含固定枚举 Literal)
frontend/src/
  pages/          Home Upload Browse Detail Search / Ideas Logs Capture Plans / Me Settings
  components/     Icon(线性SVG) TabBar Img ItemCard TokenGate ClassificationMeta ClassificationGuide
  api.js          单用户 API 客户端(token 存 localStorage)
  classification.js  前端固定枚举 + 分类说明文案(与后端 Literal 对齐)
  styles.css      暖纸(#f4f1ea)+ 墨青(#2f6f5f)主题,CSS 变量
deploy/init.sql   幂等建表(新部署首次执行);ensure_schema 覆盖增量迁移
docs/             本套文档
Dockerfile        多阶段:node 构建 dist → python 后端 + 复制 dist 到 /app/frontend/dist
docker-compose.yml  db(postgres:17)+ backend
```

---

## 2. 数据模型(要点;完整见 DATABASE.md)

**`core`(脑本体,跨入口)**
- `sources`:来源登记(origin_schema/table/id),知识/碎片/想法归位时挂。
- `knowledge`:精选脑,有 `body_tsv`(全文检索),可搜。
- `notes`:碎片收集箱,`last_seen_at` 支撑"重新遇见"。
- `tags` / `knowledge_tags`:theme/use 标签,theme 可生长。
- `entries`:**文字入口**。`kind ∈ {idea,log,plan}`(想法/日志/计划;已废弃 note/clip)。
  关键列:`body, source_item_id(来源截图), theme, promoted_at`,
  **统一 5 维**:`entry_type, domain, use_tag, source, topics(JSONB)`,
  自动分类状态:`ai_classify_status(NULL/pending/done/failed), ai_classified_at, ai_classify_output`。
- `settings`:kv(模型切换等)。
- `idea_clusters`:**尚未建**(想法簇功能设计好了没落地,见第 6 节)。

**`image`(z-image 入口)**
- `files`:原图事实源,只增不改(用户删手机后是唯一副本)。
- `items`:条目。Vision 打:`title/theme/use_tag/granularity/summary/is_ocr_suitable`,
  JSONB:`ai_output`(含 suggested_theme/quality)、`ai_insight`(问问AI缓存),
  **统一 5 维(新)**:`entry_type/domain/topics/ai_classify_status/ai_classified_at`(use_tag 沿用 Vision,source 隐含=截图)。
- `contents`:OCR 正文(raw_text/clean_text)。

**迁移机制(重要)**:`db.py::ensure_schema()` 在每次启动跑,全是 `ALTER … ADD COLUMN IF NOT EXISTS` / `CREATE … IF NOT EXISTS`,幂等。**部署只需 `git pull && docker compose up -d --build`,不用手动跑 SQL。** `init.sql` 只在全新库首次启动执行。

---

## 3. 统一分类体系(已"固定",这是核心约定)

所有内容用 5 个维度。**枚举是死的**,三处必须一致:后端 `models/entries.py` 的 `Literal` + `classify.py` 的集合 + 前端 `classification.js`。

| 维度 | 字段 | 固定值 |
|---|---|---|
| 类型 | `entry_type` | 想法/句子/规则/决策/知识/资料/记录 |
| 领域 | `domain` | 身心/生活/能力/财务/方向 |
| 用途 | `use_tag` | 方法/避坑/心态/工具/灵感/存档/决策/参考(**"证据"已统一改"存档"**)|
| 标签 | `topics` | 自由关键词数组,别人经历一律加 `他人经验` |
| 来源 | `source` | 自己/截图/文件(只表进入方式,不表可信度)|

改枚举 = 同时改这三处 + 加迁移(如果影响约束)。

---

## 4. 三条 AI 管线(全走 OpenRouter,模型各自可在 /settings 切换)

| 管线 | 函数 | 模型设置 | 触发 | 产出 |
|---|---|---|---|---|
| **消化/OCR** | `vision.call_vision` | `ocr_model` | 上传后 worker `_loop` 自动 | title/theme/use_tag/granularity/summary/quality/suggested_theme + OCR |
| **自动分类** | `classify.call_classify` | `classify_model` | worker `_classify_loop` 自动(entries + items) | entry_type/domain/topics(截图不覆盖 vision 的 use_tag/theme) |
| **问问AI** | `vision.call_insight` | `insight_model` | 详情页按需点击 | explanation/quality/quality_note/suggested_theme(缓存 `ai_insight`) |

**worker.py 两个循环并行**:`_loop`(Vision 处理 review 的 items)、`_classify_loop`(分类 pending 的 entries + ok 未分类的 items)。都受 `_take_budget()`,`VISION_DAILY_BUDGET<=0` 视为不限。失败记状态、可续跑、不阻塞。
**人工优先**:用户手改任一分类维度 → 后端置 `ai_classify_status='done'`,worker 不再覆盖。`reclassify` 端点清空 + 置 pending 重跑。

---

## 5. 前端要点

- **导航 5 tab**:首页 / 上传 / 想法 / 记录(=日志+计划入口)/ 我的(纯入口,内含 AI 设置独立页 `/settings`)。
- **详情页操作**:标签 / 精选 / 删除(**永久删,无回收站**,"不删即留下")+ 我的想法输入(存成 idea,挂 source_item_id)。
- **想法页**:记 + AI 自动分类(`ClassificationMeta` 可编辑类型/领域/用途 + 标签增删 + 重新分类)+ 精选入脑。
- **主题风格**:暖纸底 + 墨青主色 + 线性 SVG 图标(`components/Icon.jsx`),CSS 变量在 `styles.css :root`。
- **鉴权**:`TokenGate` + token 存 localStorage,`api.js` 每请求带 `Authorization: Bearer`。

---

## 6. 当前状态 / 待办 / 已知问题

### 已完成(v0.3 主体)
捕捉、消化、问问AI、搜索(截图+手写)、永久删除、模型三处分开配、文字入口(想法/日志/计划)、想法(编辑/打主题/精选)、**统一 5 维分类 + AI 自动分类(entries + items 都已接)**、暖纸墨青视觉 + 线性图标、AI 设置独立页。

### 待办(非向量,按优先级)
1. **首页整理**:首页偏杂,尚未收拾(上下文原因暂停)。需先问用户"哪里最碍眼"再动。
2. **想法簇 / 合并**:设计已定稿(见 BLOCKS.md)但**未落地**。要点:合并=分组不删、保留每条、展开看**演变时间线**、频次自动+手改、代表概括可写可选一条、拆分可逆。要建 `core.idea_clusters(id,gist,times,…)` + `core.entries.cluster_id` + 端点 + Ideas 页多选合并 UI。**AI 建议合并留到向量批**。
3. **追问(板块4)**:AI 就截图抛 2-3 个思考问题逼你想深。主循环高价值下一步,未建。
4. **重新遇见(板块3)**:引擎,但现在推的是碎片(`core.notes`)不是**截图**,需重做成推截图 + 当场写想法。
5. **质量补丁**:删原图留文字、编辑 OCR 正文(裁剪明确不做=整理花园陷阱)。

### 明确推迟
**向量 / pgvector / 语义聚合 / 存量导入 / AI 建议合并**——用户要求放到最后。方案已议(本地 bge 中文 embedding + pgvector,对 summary/body 算,先近邻后聚类)。

### 已知问题 / 需留意
- **theme 与 domain 并存**:entries/items 上旧 `theme`(生长分类)和新 `domain`(5 维)暂时共存,冗余,以后要理顺(可能 domain 取代 theme,或 theme 降级为 topics)。截图仍有 theme/use_tag/granularity 三个旧维度。
- **待用户确认**:生产 Vision 是否真在跑。若截图详情"全空/待处理"→ 检查 `.env` 的 `OPENROUTER_API_KEY` 和 `/settings` 里的模型是否有效。诊断:`docker compose logs --tail=50 backend | grep -iE "vision|worker|error"`。首页/浏览页生长分类不显示的 bug 已修(动态渲染 dimensions)。
- **命名**:软件名待定,候选 Echo/回响、Muse、Prism、拾光(推荐 Echo)。README/docs 里仍叫 zbrain。

---

## 7. 本地开发与验证

- **venv**:`backend/.venv`(用 `C:/Users/momol/AppData/Local/Programs/Python/Python312/python.exe` 建;原 venv 曾指向失效的 F:\Python)。
- **本地 DB**:Postgres 库 `zbrain`,密码 `123456`(`backend/.env` 的 DATABASE_URL 已改成这个;注意 .env 默认曾是 `zbrain2024` 对不上)。
- **跑后端**:`./.venv/Scripts/python.exe -m uvicorn main:app`。前端:`cd frontend && npm run dev`(vite,代理 /api → 127.0.0.1:8000)。或根目录 `./start-dev.ps1`。
- **验证套路**:后端改动 `py -3 -m py_compile <files>`;前端 `npm run build`;逻辑用直连 DB 的 E2E 脚本(`PYTHONPATH=backend DATABASE_URL=…123456… python <script>`)。真 AI 验证需 OpenRouter key(**不在仓库,向 owner 要测试 key**)。
- **注意**:Windows 控制台中文会显示成 GBK 乱码(数据本身没问题;要看中文就写 UTF-8 文件再读)。前端 preview 截图工具偶尔超时,可改用 DOM 查询验证。

## 8. 部署与运维

```bash
cd /opt/1panel/apps/z-image      # 1Panel,Postgres 容器 1Panel-postgresql-WRvF,库 zbrain,user user_e5JPdJ
git pull
docker compose up -d --build     # ensure_schema 自动迁移,分类 worker 自动补跑存量
docker compose logs -f backend
```
- `.env` 必改:`POSTGRES_PASSWORD / AUTH_TOKEN / OPENROUTER_API_KEY`;`VISION_DAILY_BUDGET=0`(不限次,交给 API 侧限流)。
- **原图备份**:落宿主机 `/data/zbrain/files`,用户删手机后是唯一副本(用户另有磁盘备份 + Google 相册,已三重)。
- **白屏坑(已修)**:`main.py` 用 `_DIST_CANDIDATES` 兼容容器(`/app/frontend/dist`)与本地(`../frontend/dist`)两种布局——别改回单一 `parent.parent`。

---

## 9. 从哪接着做

推荐顺序:**先问用户首页痛点做首页整理(小)→ 想法簇合并(中,设计现成)→ 追问(中,主循环高价值)→ 重新遇见重做(大,引擎)**。向量永远留最后。动任何新功能前,先对照 FRAMEWORK.md 的"带偏自查"三条:它服务主循环吗?是不是又在做整理花园?心脏(重新遇见)补了吗?
