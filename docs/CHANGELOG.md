# 变更历史 · CHANGELOG

> 记录每个版本的详细变化,便于回溯设计演进。按语义版本归纳,附对应 commit。
> 规划中的方向见 [`../v0.3-plan.md`](../v0.3-plan.md)。

---

## v0.3.x — 统一分类与工程交接（2026-07-05）

- `b2d6301`：`core.entries` 增加类型/领域/用途/标签/来源及分类状态；前端展示与分类说明。
- `52316b2`：统一领域、用途说明口径，“证据”改为“存档”。
- `221301e`：文字 Entry 后台自动分类，支持人工优先和重新分类。
- `b83e469`：OCR、问问 AI、自动分类模型拆分设置；AI 设置独立页面。
- `6e848d4`：截图接入统一类型/领域/topics 分类并在详情页展示；保留旧 theme/use/granularity。
- `f85470d`：增加工程交接总文档。
- 当前文档补全：新增 STATUS/FRAMEWORK/DECISIONS/TESTING，同步 API、DATABASE、BLOCKS，并增加无数据库/无 AI 的分类契约测试。

兼容约定：`kind` 不等于 `entry_type`；`theme` 与 `domain` 暂时并存；分类失败需手动重新分类。

## v0.3.0 — 智能整理 + 文字入口 + 视觉升级(2026-07-04)

从"能存"迈向"会整理",并开了第二个入口(文字)。分批交付:

### 问问 AI + 搜索修复 · `29f1d9c`
- **搜索 bug 根治**:原来只搜 `core.knowledge`(已入脑),用户几乎不入脑 → 搜啥都空。改为搜**全部条目**(`image.items` 的标题/摘要/正文,ILIKE 子串 + 片段预览,结果可点进详情)。
- **详情页「问问 AI」**(`POST /api/items/{id}/insight`):按需触发(拉不推)、结果缓存进 `image.items.ai_insight`。
  - 看法/定义:标「AI 补充」,与原文事实源分开。
  - 质量标签:干货/反面样本/无信息量(红线:鸡汤≠该删,反面样本有避坑价值)。
  - 单条分类建议 + 一键采纳(`POST /{id}/adopt-theme`:建 tag + 归入)。
- 新增列 `image.items.ai_insight`;运行时迁移 `db.ensure_schema()`(已部署库不重跑 init.sql)。

### 分类自动生长 · `68bf9aa`
- 每张图上传后**本来就在跑的那次自动 Vision**,顺手多判 `suggested_theme`(零额外调用):`life`/`other` 兜底类若能归更具体领域(运动/情绪…)则给候选,存进 `ai_output`。
- 聚合冒泡(`GET /api/stats/theme-candidates`):候选攒够阈值(默认 3)才在浏览页冒一次"发现一簇 X,建吗",**不逐条推、忽略本地记住**。
- 批量采纳(`POST /api/stats/theme-candidates/adopt`):建 tag + 整簇归入。
- 已知局限:模型对同类可能给不同措辞(健身/运动)→ 文本聚合分散,语义归一留给向量批。

### 文字入口 + 清库 · `a7c06f5`
- **新表 `core.entries`**(kind 区分:速记/日志/计划/剪藏),复用 core,不新开平行表。
  - 速记/剪藏 → 待整理 Inbox → 归位进 `core.notes`/`core.knowledge`(建 sources 指向 entry,来源可追溯)。
  - 日志:带日期、按天翻、往年今天(`GET /entries/logs/on-this-day`)、可选心情;绝不 streak。
  - 计划:pinned 常驻首页。
  - 后端 `routers/entries.py` + `models/entries.py`。
- **清库仪式**:自动线 Vision 顺手判 `quality` 存 `ai_output`;`GET /api/items/cleanup` 列出"无信息量"的,主动进入才聚合,不推送不计数。
- 搜索扩展:同时覆盖截图条目 + 手写文字(`SearchHit.source` 区分)。
- 前端新增 Capture/Inbox/Logs/Cleanup 页;TabBar 加「记」;首页加计划区 + 文字入口 + 清库入口。

### UI 统一收敛 · `6c41fd7`
- 卡片统一为阴影卡(去描边)、标签统一胶囊、小按钮归一、首页文字入口三连改带图标居中、计划便签去突兀黄块。

### 视觉升级「暖纸 + 墨青」· `1bbc079`
- 配色从冷灰蓝换成暖米纸底 + 墨青绿主色 + 靛/赭大地色标签;柔和暖阴影(`--shadow`/`--shadow-lg` 变量化);圆角 16→18;标题加大加重。

### 线性图标系统 · `66ada43`
- 新增 `components/Icon.jsx`(home/plus/pen/trash/book/inbox/flag/spark/search),把导航栏及全局的 emoji 图标换成统一单色线性 SVG(跟随 currentColor,粗细/尺寸一致)。

---

## v0.2.0 — 部署套件 + 体验补丁(2026-07-03)

### 部署套件 · `7a487fe`
- 单容器全栈(前端 dist 打进后端镜像,单端口 8000)+ 自带 PostgreSQL(首次启动自动执行 `deploy/init.sql`)。
- `Dockerfile` 多阶段构建、`docker-compose.yml`(postgres + backend,healthcheck 后再起后端)。

### 完整 README · `39685e2`
- 功能全貌 + 中文部署指南。

### 体验补丁 · `3744ba4`
- 全部入口打通、处理进度可见(只显示"在不在整理",不显示待办数字)、新增 `asset` 资料粒度(证件/票据类不入脑仅存档)。

---

## v0.1.0 — MVP 五步(2026-07-03)

按 `zbrain-claude-code-buildbook.md` 五步施工手册顺序推进:

| 步 | commit | 内容 |
|---|---|---|
| ① | `0c1c096` | 数据库 + 后端骨架 + 单用户 header token 鉴权 |
| ② | `16ae7c0` | 上传管线(同步落库即返回,不接 AI):checksum 去重、原图落盘 |
| ③ | `f0af56d` | 接 Vision 后台处理:worker 轮询 + 每日预算 + 失败重试;两段式省钱(先判是否值得 OCR) |
| ④ | `cf91f41` | iPhone 前端(React + Vite + PWA):Upload/Home/Browse/Detail/Trash/Search |
| ⑤ | `7da4153` | 消化闭环:闸门一 review → 闸门二 promote 入脑 / fragment 落箱 |

**架构蓝图**:`zbrain-architecture-v3.md`(what/why、完整 schema、Vision prompt)。

---

## 版本号约定
- 主版本聚焦一个大主题(v0.1 能存、v0.2 能部署、v0.3 会整理 + 文字入口)。
- 下一步方向(向量语义聚合 / 存量导入 / 文字入口时间流重构 / 计划体系)见 [`../v0.3-plan.md`](../v0.3-plan.md)。
