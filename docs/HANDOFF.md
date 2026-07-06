# 项目交接文档 · zbrain / z-image

> 更新于 2026-07-06。当前 `main` 已推送到 GitHub `mikemoi/z-image`，最新已知提交：
>
> - `3204a64` `fix: batch 3 - search merge-sort/escaping + detail page shows linked ideas`
> - `dfbc00d` `feat: batch 2 - thumbnail generation + HTTP caching pipeline`
> - `d5d8dbf` `fix: batch 1 code review fixes (checksum uniqueness, classify retry, tz, auth)`
> - 上一关键提交：`43a6445` `Clean fixed subtopics and candidate tracking`
>
> 这三个提交是对 [CODE_REVIEW_2026-07-06.md](CODE_REVIEW_2026-07-06.md) 全面代码审查的修复：checksum 唯一约束
> + 原子 upsert（原图误删风险）、分类空结果不再误标完成 + 失败自动重试、往年今天时区 bug、鉴权常量时间比较、
> 缩略图生成 + 一年期缓存头（截图列表流量从原图降到长边 960px）、搜索合并排序 + LIKE 转义、详情页显示已绑定的想法。
> `CODE_REVIEW_2026-07-06.md` 里仍有未做项（候选原子 upsert、集成测试骨架等），按里面的优先级顺序继续。
>
> **同日（2026-07-06）新增、尚未提交**：数据概览页新增"主题词频统计"入口，见 [6.1 主题词频统计](#61-主题词频统计新增)。
> 已在本地验证（单测 16 个通过、前端 build 通过、手动过一遍浏览器交互），改动还在工作区，下一位接手者可以直接
> `git status`/`git diff` 看到，决定要不要提交。
>
> 本文件是下一位接手工程师的入口。读完它，再看 [STATUS.md](STATUS.md)、[DATABASE.md](DATABASE.md)、[API.md](API.md)、[TESTING.md](TESTING.md) 和 [FRAMEWORK.md](FRAMEWORK.md)。

---

## 0. 这是什么

zbrain / z-image 是一个单用户、自托管的第二脑系统。它不是收藏夹，也不是待办整理工具，而是把日常截图、想法、日志和计划持续转化成可搜索、可重新遇见、可追问、可沉淀的个人认知资产。

主循环：

```text
捕捉 → 后台消化 → 重新遇见 → 追问 → 产生想法 → 精选
```

三条产品准绳：

- **anti-anxiety**：不做 streak、红点、待办数量和清理焦虑。
- **self-use**：成功标准是用户真的持续用、手机截图真的能清空。
- **别做整理花园**：分类服务于使用和重新遇见，不制造人工维护目录的负担。

---

## 1. 技术栈与运行方式

- 后端：FastAPI / Python 3.12
- 数据库：PostgreSQL 17，schema 为 `core` 和 `image`
- 前端：React + Vite + PWA，iPhone 竖屏优先
- AI：OpenRouter Chat Completions，默认 `openai/gpt-4.1-mini`
- 部署：Docker Compose，Postgres + 单后端容器，前端 dist 打进后端，单端口 `8000`
- 原图：宿主机 `/data/zbrain/files`，用户删手机后这里可能是唯一副本，必须备份

本地开发：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload

cd ..\frontend
npm run dev
```

或根目录：

```powershell
.\start-dev.ps1
```

生产更新：

```bash
git pull
docker compose up -d --build
docker compose logs -f backend
```

`backend/db.py::ensure_schema()` 会在启动时幂等补迁移；全新库首次启动由 `deploy/init.sql` 建表。

---

## 2. 目录结构

```text
backend/
  main.py                  FastAPI 入口，启动连接池、ensure_schema、worker，挂载前端 dist
  config.py                环境变量
  db.py                    PostgreSQL 连接池 + 运行时迁移
  auth.py                  单用户 Bearer token
  vision.py                截图 Vision/OCR + 问问 AI
  classify.py              最终内容坐标分类 prompt + normalize
  classification_schema.py 最终分类常量：类型/领域/主题/子题/来源与校验
  worker.py                Vision worker + 分类 worker + 候选累计
  routers/
    items.py               截图上传、详情、浏览、批阅、今日推荐、删除
    entries.py             想法/日志/计划、时间线
    admin.py               重新整理排队
    candidates.py          候选标签/候选子题审批
    search.py              全文搜索 + 全部/我的/外部范围
    stats.py               数据概览
    ...
  models/
    entries.py / items.py  Pydantic 模型和契约
frontend/src/
  classification.js        前端最终分类常量，与 backend/classification_schema.py 对齐
  api.js                   API 客户端
  pages/
    Home Upload Browse Detail Search
    Capture Logs Ideas Plans
    Me Overview Settings Trash ReviewSession
    Timeline Reclassify Approvals
  components/
    ClassificationMeta ClassificationGuide EntryEditor ItemCard ...
deploy/init.sql            新库建表
docs/                      文档
```

---

## 3. 当前数据模型要点

### core

- `core.entries`：文字入口，`kind ∈ {idea, log, plan}`。
  - 手写内容默认 `source=我`。
  - `kind=idea` 默认 `entry_type=想法`。
  - `kind=log` 默认 `entry_type=记录`，`logged_for` 为空时按 Europe/Madrid 今天。
  - 图片详情页写想法时：`source=我`，同时保留 `source_item_id`。
- `core.knowledge` / `core.notes`：旧精选脑和碎片收集箱，兼容保留。
- `core.classification_candidates`：候选标签/候选子题池。
  - 唯一键：`candidate_type + name + domain + main_topic`
  - 有 `source_counts`，记录 `我/图片/文件` 来源分布。

### image

- `image.files`：checksum 去重后的原图事实源。
- `image.items`：截图条目。
  - 截图默认 `source=图片`。
  - Vision 仍写旧字段 `theme/use_tag/granularity/summary/quality/suggested_theme`。
  - 最终内容坐标由分类 worker 写入。
- `image.contents`：OCR 正文。

旧字段 `theme/use_tag/granularity/topics/promoted_at/highlights` 不删除，继续兼容旧链路。新分类主路径不依赖它们。

---

## 4. 最终内容坐标

当前已实现最终稳定版：

```text
类型：想法 / 知识 / 资料 / 记录 / 规则
领域：身心 / 生活 / 能力 / 财务 / 方向
主题：领域下固定 6 个主题
子题：主题下固定细分
相关：最多 2 个相关主题
标签：细节关键词
来源：我 / 图片 / 文件
```

旧值兼容：

```text
entry_type: 句子 → 想法，决策 → 规则
source: 自己 → 我，截图 → 图片
```

重要规则：

- `main_topic` 必须属于 `domain`。
- `sub_topic` 必须属于 `main_topic`；没有合适子题用 `未细分`。
- `related_topics` 是主题级，不是子题级，最多 2 个，不能重复，不能包含主主题。
- AI 不能新增正式类型、领域、主题、子题、来源。
- AI 不能直接创建正式标签或正式子题，只能提名候选。
- `highlights` 是人工重点，分类/重新整理不再生成或覆盖它。

固定子题表维护在两处：

- 后端：[backend/classification_schema.py](../backend/classification_schema.py)
- 前端：[frontend/src/classification.js](../frontend/src/classification.js)

改子题时必须同步这两处，并更新测试。

最近一次子题清理已完成：

- 删除固定子题：`洗澡`、`居住/住家证明`、`编程/Docker`、`编程/部署`、`产品/第二脑`、`产品/分类系统`、泛化的 `风险`
- 改名：`债务/风险 → 债务风险`，`投资/风险 → 投资风险`
- 新增：ADHD 下 CBT/反馈/启动相关子题，学习方法/理解/复述/内化/构建体系，交易周期/扛单/重仓，落子无悔，情绪转化等

---

## 5. AI 管线

### 1. Vision/OCR

- 函数：`vision.call_vision`
- 触发：上传后 worker 自动处理 `image.items status='review'`
- 产出：标题、摘要、旧 theme/use/granularity、OCR、quality、suggested_theme

### 2. 最终内容坐标分类

- 函数：`classify.call_classify`
- 触发：worker `_classify_loop`
- 对象：`core.entries` + `image.items`
- 产出：

```json
{
  "entry_type": "知识",
  "domain": "能力",
  "main_topic": "学习",
  "sub_topic": "学习方法",
  "related_topics": [],
  "tags": ["认知层次"],
  "candidate_tags": [],
  "candidate_sub_topic": null,
  "candidate_sub_topic_domain": null,
  "candidate_sub_topic_main_topic": null
}
```

如果固定子题不够准确：

```text
sub_topic = 未细分
candidate_sub_topic = AI 提名
```

候选进入 `core.classification_candidates`，来源包括 `我/图片/文件`，达到默认阈值 5 次后在“我的 → 待审批”显示。

### 3. 问问 AI

- 函数：`vision.call_insight`
- 触发：详情页主动点击
- 结果缓存到 `image.items.ai_insight`
- 是 AI 补充，不是原文事实源

---

## 6. 前端当前入口

底部导航 5 个：

- 首页
- 上传
- 想法
- 记录
- 我的

“我的”当前包括：

- 集中批阅
- 数据概览
- 时间线
- 重新整理
- 待审批
- AI 设置
- 长期计划
- 回收站
- 分类说明

搜索页支持范围：

```text
全部：不限制 source
我的：source = 我
外部：source IN (图片, 文件)
```

今日推荐逻辑：

- 接口：`/api/items/recommendations`
- 只从未删除、`status='ok'` 的图片条目中取
- 优先未看过，再按较久没看排序
- 分类只展示，不参与推荐排序

集中批阅逻辑：

- 接口：`/api/items/review-queue` 和 `/api/items/review-facets`
- 只取未删除、`status='ok'`、`reviewed_at IS NULL` 的图片条目
- 分类入口支持类型、领域、主题、来源、高频标签
- 子题目前只展示，不作为批阅入口分组

### 6.1 主题词频统计（新增）

背景：用户想看"某个主题下（比如交易），哪些子题/标签出现得多"，能点进去看趋势和具体是哪几条内容说的。

设计取舍（讨论记录，供以后加类似统计时参考）：

- 词的口径选的是"已定型的分类结果"（`sub_topic` + `tags`），不做正文自由分词——中文分词要引入 jieba 之类的库，
  还要处理噪音词/简繁体，工程量明显更大，而 `sub_topic`/`tags` 是分类时已经产出的结构化字段，直接 `GROUP BY` 就够。
- 范围锁定在选中的一个 `main_topic`（如"交易"），不做全库自由词云。
- `未细分` 是子题的兜底桶，不是真实词，统计时排除。
- 入口挂在数据概览页——点"主题"那一行（如"交易"）直接跳转，不单独做一个主题选择器，复用概览页已经在展示的数据。
- 数据概览和主题词频统计的计数 SQL 已经合并成共享辅助函数 `_dimension_counts()`（`backend/routers/stats.py`），
  两处都是"未删除的 entries+items 按某字段分组计数"，唯一区别是有没有 `main_topic` 过滤。
- **集中批阅的"按分类批阅"（`/api/items/review-facets`）刻意没有并进来**：它的语义是"挑一批还没看过的内容去批阅"，
  范围锁定 `reviewed_at IS NULL AND status='ok'` 且只查 `image.items`（不含手写 entries），是导航/筛选工具而不是
  统计展示。为了复用而把这个过滤逻辑也塞进 `_dimension_counts()`，会让函数长出一堆 if-scope 分支，不值得。

接口（`backend/routers/stats.py`）：

- `GET /api/stats/topic-terms?main_topic=交易`：该主题下 sub_topic + tag 的出现次数排行榜。
- `GET /api/stats/topic-terms/items?main_topic=交易&term=重仓&type=tag|sub_topic`：点某个词，看命中的具体内容
  （截图 or 手写条目），按时间倒序，供跳回原文。
- `GET /api/stats/topic-terms/trend?main_topic=交易&term=重仓&type=tag|sub_topic&granularity=week|month`：
  该词随时间的出现次数，前端画简单柱状图。

前端：`frontend/src/pages/TopicStats.jsx`，路由 `/overview/topic/:mainTopic`。`Overview.jsx` 里"主题"那个
`StatSection` 传了 `onSelect`，点击行会跳过去；其余维度（类型/领域/子题/来源/分类状态）没传 `onSelect`，行为不变。

踩过的坑：`core.entries` 表没有 `title` 列（只有 `body`），第一版把 entries 分支的 `SELECT` 也写了
`e.title` 直接借用了 items 那边的字段名，本地联调时才炸出 `UndefinedColumn`。已修（`topic_term_items` 里
entry 分支现在是 `NULL AS title`）。以后往 `core.entries`/`image.items` 的联合查询里加字段，记得两张表列不完全对齐。

---

## 7. 重新整理

入口：`我的 → 重新整理`

接口：`POST /api/admin/reclassify`

支持：

```text
scope: all / mine / external / unclassified / entries / items
mode: fill_missing / force
```

行为：

- 只排队，不同步调用大量 AI
- 先做确定性兼容修正：
  - `自己→我`，`截图→图片`
  - `句子→想法`，`决策→规则`
  - 旧子题迁移，如 `洗澡→清洁 + #洗澡`、`编程/Docker→服务器/Docker + 相关：编程`
- `fill_missing` 默认只补缺失，不清空已有分类
- `force` 会清空分类后重算，前端有确认
- 不处理正文、OCR、图片、highlights、promoted_at、source_item_id 和旧字段

---

## 8. 当前已知问题与风险

- 生产 AI/worker 健康不能从仓库判断，要看 `/api/worker/status` 和后端日志。
- 自动分类失败状态 `failed` 不会自动重试，需要手动重新分类或重新整理排队。
- README、旧架构蓝图、v0.3 规划文档仍含历史表述；当前真实状态以 `HANDOFF/STATUS/API/DATABASE/TESTING` 和源码为准。
- 暂无隔离测试数据库；自动测试均不连真实 DB、不调真实 AI。
- 候选批准目前只改候选状态为 `active`，不会自动把候选名写回固定表代码；正式扩充固定子题仍需要改 `classification_schema.py` 和 `classification.js`。
- `NEXT_HANDOFF_CLASSIFICATION.md` 是历史需求记录，内容已基本实现，不再代表未开工状态。

---

## 9. 下一步建议

优先级建议：

1. **生产部署并用“重新整理”跑一轮旧数据**：确认 source/type/sub_topic 迁移和候选累计表现。
2. **观察“待审批”候选质量**：尤其学习、ADHD、交易、日常记录这些高频领域。
3. **OCR 正文排版优化**：当前识别后正文仍可能碎行，适合做规则化清洗，不增加 AI 调用。
4. **记录 → 近日**：轻量备忘/购物清单，不做 Todo 系统。
5. **想法簇/可逆合并**：设计已定，尚未实现。
6. **追问**：围绕截图生成 2-3 个促使用户思考的问题，是主循环高价值下一步。
7. **重新遇见重做**：当前更多还是 notes/推荐图片，应重做成“截图 → 当场写想法”的闭环。
8. **向量/pgvector/语义聚合/存量导入**：明确放最后。

---

## 10. 验证

每次交付前至少跑：

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q .

cd ..\frontend
npm run build
```

最近一次验证通过（2026-07-06，含本次主题词频统计改动）：

- 后端单测：16 tests OK
- 后端 compileall：OK
- 前端 build：OK
- 手动过一遍：起本地前后端，往 `core.entries` 插了两条 `main_topic='交易'` 的临时测试数据，
  确认「数据概览 → 点交易 → 词频榜 → 点复盘 → 看到趋势图 + 两条原文」全链路通，测试完已清理。

主题词频统计的接口目前只有手动验证，还没补自动化测试（`topic_terms`/`topic_term_items`/`topic_term_trend`），
如果要往这几个接口加逻辑，建议先补 `tests/` 下的契约测试。

---

## 11. 最近提交

```text
3204a64 fix: batch 3 - search merge-sort/escaping + detail page shows linked ideas
dfbc00d feat: batch 2 - thumbnail generation + HTTP caching pipeline
d5d8dbf fix: batch 1 code review fixes (checksum uniqueness, classify retry, tz, auth)
16f0b03 docs: add code review notes and pending requirements draft
afa712a Update project handoff after classification work
43a6445 Clean fixed subtopics and candidate tracking
```
