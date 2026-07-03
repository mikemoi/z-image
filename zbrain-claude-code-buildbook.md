# zbrain · Claude Code 施工手册

> 配套文档:`zbrain-architecture-v3.md`(架构蓝图,讲 what/why)。
> 本手册讲 how:把项目拆成可执行、可验收的分步任务。Claude Code 按此逐步施工。
> 读者:Claude Code。使用者:项目所有者(单用户,iPhone 17 Pro Max 为主要使用设备)。

---

## A. 给 Claude Code 的项目启动说明(开工前必读)

**你要建什么:** zbrain —— 一个自托管、单用户的"第二脑"综合存储库。第一个入口是 z-image:把手机截图变成带标签的、可检索/可重新遇见的知识。完整架构见 `zbrain-architecture-v3.md`,务必先通读该文档第 0-4 节(本质、数据教训、架构、schema)。

**最高准绳:** "方便我用" 压倒 "存得全"。三条气质贯穿全程:anti-anxiety(无 streak/无待办计数/删除无劝阻)、self-use(成功=我真的天天用、手机真的清空)、别造整理花园(自动流水线优先,不逼用户手动经营)。

**技术栈(固定,不要替换):**
- 后端:FastAPI(Python)
- 数据库:PostgreSQL(已运行,直接用,库名 `zbrain`;不要用 SQLite)
- 前端:React + Vite + PWA,单页应用,**按 iPhone 17 Pro Max 竖屏大屏优化**
- AI:OpenRouter,Vision 模型 `openai/gpt-4.1-mini` 或 `google/gemini-flash`
- 部署:Docker;可前后端合并(FastAPI 挂载前端 dist)
- 原文件:存磁盘 `/data/zbrain/files/`,DB 只存路径+checksum

**施工方式(重要):** 严格按下面五步走,一步一交付一验收。**不要一次性写完整个项目。** 每步做完停下,等所有者在手机上真实验收通过,再进行下一步。每步都要能独立运行、独立验收。

**代码规范:** 命名全小写下划线;所有列表查询默认 `WHERE deleted_at IS NULL`;所有外部调用(Vision/DB)包 try-catch,失败不阻塞主流程、落 review 兜底;单用户,鉴权用一个环境变量里的 header token 即可。

**iPhone 大屏前端要点:** 竖屏空间充裕,重新遇见卡片配大缩略图(一屏 3-4 张);详情页原图大图展示(长文截图要能直接读清);双维度筛选做成舒适网格不挤成小标签;操作按钮(删除/入脑/改标签)放下半屏拇指热区。

---

## B. 五步施工计划总览

| 步 | 交付 | 验收(所有者能看到/做到) |
|---|---|---|
| 1 | 数据库 + 后端骨架 + 鉴权 | 库和表建好;FastAPI 能起;健康检查接口通 |
| 2 | 上传管线(不接 AI) | 手机选图上传→秒回"已接收 N 张"→原图落磁盘、记录落库 |
| 3 | 接 Vision 处理 | 上传的图后台被自动判 title/theme/use/granularity/summary/OCR,落库 |
| 4 | 前端主界面 | 手机上能看首页(重新遇见+维度入口)、列表、详情、删除 |
| 5 | 消化闭环 | 能 review、能入脑(knowledge→core.knowledge)、能落碎片(fragment→core.notes) |

---

## C. 第一步:数据库 + 后端骨架 + 鉴权

**目标:** 打地基。无 AI、无前端、无业务逻辑,只要库、表、项目结构、鉴权跑通。

**做什么:**
1. 在已运行的 PostgreSQL 上创建库 `zbrain`,建三个 schema(`core` / `image`)和全部表。**直接使用 `zbrain-architecture-v3.md` 第 4 节的完整 SQL**(core.sources/knowledge/notes/tags/knowledge_tags,image.files/items/contents,含所有索引和 tags 初始数据)。
2. 搭 FastAPI 项目结构:`main.py`、`db.py`(连接池)、`auth.py`(header token 校验,token 从环境变量读)、`routers/`(先空)、`models/`(Pydantic 模型)。
3. 一个健康检查接口 `GET /api/health`,返回 `{"status":"ok","db":"connected"}`,验证 DB 连得上。
4. Dockerfile + docker-compose(FastAPI + 连接外部 PG),`.env.example`(DB 连接串、AUTH_TOKEN、OPENROUTER_API_KEY 占位)。

**不做:** 任何上传、AI、前端、业务接口。

**验收标准:**
- `docker compose up` 能起来
- `psql zbrain` 能看到全部表,`SELECT * FROM core.tags` 能看到预置的 theme/use 标签
- 带正确 token 请求 `/api/health` 返回 ok;不带/错误 token 返回 401

---

## D. 第二步:上传管线(不接 AI)

**目标:** 跑通"上传即走、手机可清空"的核心体感。先不接 Vision,用占位处理。

**做什么:**
1. `POST /api/items/upload`,接收多张图片(multipart)。对每张:
   - 算 sha256 → 存到 `/data/zbrain/files/image/<checksum>.<ext>`(已存在则跳过存储,复用)
   - INSERT `image.files`(file_path/file_type/original_filename/checksum/file_size)
   - INSERT `image.items`(file_id, status='review')
   - **同步完成上面这些,立即返回** `{"received": N, "message": "已接收 N 张,手机可清空"}`
2. `GET /api/items?status=&deleted=false` 列表(先返回基础字段,分页)
3. `GET /api/items/{id}` 详情
4. `GET /api/files/{checksum}` 返回原图(供前端和 iPhone 展示)
5. 软删接口 `PATCH /api/items/{id}/soft-delete`、恢复 `POST /api/items/{id}/restore`、彻底销毁 `DELETE /api/items/{id}/purge`(purge 要真删磁盘文件+记录)

**关键:** 上传接口必须"同步落库即返回",绝不在上传请求里等任何慢操作。为第三步预留:items 建好后有个"待处理"状态(status='review' 且 ai_output 为空即待处理)。

**不做:** Vision、清洗、前端。

**验收标准:**
- 用 curl 或 Postman 传几张图,秒回"已接收 N 张"
- 磁盘 `/data/zbrain/files/image/` 下出现 checksum 命名的原图
- `image.files` / `image.items` 有对应记录
- 传同一张图两次,磁盘只有一份文件(checksum 去重生效)
- 软删后列表查不到、回收站(deleted_at 非空)查得到;purge 后磁盘文件消失

---

## E. 第三步:接 Vision 处理

**目标:** 上传的图被后台自动分析,落 title/theme/use/granularity/summary,适合的做 OCR+清洗。

**做什么:**
1. 后台任务机制(FastAPI BackgroundTasks 或简单轮询 worker):捞 status='review' 且未处理的 item,逐个处理。**可续跑、失败重试、限每日调用预算**(预算从环境变量读)。
2. 对每个 item:把原图发给 OpenRouter Vision,**使用 `zbrain-architecture-v3.md` 第 6 节的完整 prompt**,强制 JSON 返回 `{title, theme, use, granularity, summary, is_ocr_suitable, ocr_text?}`。
3. 解析返回:
   - 更新 `image.items`(title/theme/use_tag/granularity/summary/is_ocr_suitable/ai_output,status='ok')
   - 若 is_ocr_suitable 且有 ocr_text:机械清洗(见下)→ INSERT `image.contents`(raw_text=ocr_text, clean_text, extraction_method='vision')
   - 任何步骤失败:status 保持 'review',记 log,不阻塞下一个
4. **机械清洗函数**(在 ocr_text 上跑):去除状态栏残留文本、纯 URL 行、跨行重复的页眉页脚样式行、明显 UI 词(点赞/关注/回复/搜索等)。规则从简,主力剥离已由 Vision prompt 完成,这里只做兜底。

**JSON 解析要稳:** Vision 可能返回带 markdown 包裹或多余文字,解析前 strip ```json 围栏、取第一个 {} 块,失败则落 review。

**不做:** 前端、入脑逻辑。

**验收标准:**
- 传 10 张真实图(交易方法论、交易避坑情绪帖、ADHD文章、AI工具、纯金句碎片、K线图),后台跑完后:
  - 文字类:theme/use/granularity/summary 判得合理,clean_text 里没有状态栏/点赞数/用户名
  - K线/图解类:is_ocr_suitable=false,只有 summary 且描述了图讲什么
  - 金句碎片:granularity=fragment
  - 有 title 的(知乎问题):title 被抓到
- Vision 调用失败的 item 停在 review,不影响其他

---

## F. 第四步:前端主界面(iPhone 大屏)

**目标:** 手机上能真实使用:上传、看首页、浏览、看详情、删除。

**做什么(React + Vite + PWA,iPhone 17 Pro Max 竖屏优化):**
1. **上传页:** 调系统相册多选 → 上传 → 大字反馈"✓ 已接收 N 张,手机可清空"。**不显示"待处理"计数。** 上传后引导用户去删手机原图。
2. **首页:** 上半"重新遇见"卡片区(先接 `GET /api/feed/resurface`,取 core.notes 中 last_seen_at 最久的几条,配原图大缩略;暂无 notes 时可先展示最近入库项占位);下半维度入口网格(用途:避坑/心态/方法/工具/灵感 + 主题:trading/ai/adhd/language/life),每个显示数量。顶部搜索框。
3. **浏览页:** 点维度进入,双维度可叠加筛选(如 use=避坑 跨所有主题),列表卡片:大缩略图、title、theme/use 标签、summary、状态。
4. **详情页:** 原图大图(可捏合放大,长文能读清)+ title + theme/use + summary + clean_text + 底部操作区(拇指热区):改标签 / review / 删除。
5. **删除体系:** 每个卡片和详情页都有删除(一键软删,无劝阻确认);回收站页(软删项,可恢复/彻底销毁,仅彻底销毁二次确认);**重新遇见卡片上也要能当场删**。

**iPhone 要点重申:** 大缩略图、大图详情、舒适网格、底部操作热区。PWA 可加到主屏。

**不做:** 入脑闭环(下一步)。删除的软删可用,入脑按钮先占位。

**验收标准:**
- iPhone 上把 PWA 加到主屏,能从相册选图上传、秒见"已接收"
- 首页能看到维度入口和数量;点"避坑"能看到所有避坑类
- 详情页原图清晰、长文截图能读;能改标签、能一键删除
- 回收站能恢复/彻底销毁

---

## G. 第五步:消化闭环(入脑)

**目标:** 打通从"图"到"第二脑"的最后一环:review → 入脑。

**做什么:**
1. **闸门一 review:** `PATCH /api/items/{id}/review` 置 reviewed_at。前端详情页"标记已看"。
2. **闸门二 入脑(knowledge 类):** `PATCH /api/items/{id}/promote`(前提 reviewed_at 非空):
   - 取 clean_text(is_current)→ 切块(初版简单按段落/长度切)
   - INSERT `core.sources`(origin='image.files', origin_id=file_id)
   - 逐块 INSERT `core.knowledge`(title, body, seq, summary)
   - 按 item.theme/use_tag 及 AI 建议的 topic,建 `core.knowledge_tags`(theme/use 标签已预置;topic 标签不存在则先 INSERT core.tags kind='topic')
   - 置 promoted_at
3. **碎片落箱(fragment 类):** `POST /api/items/{id}/to-note` → INSERT `core.notes`(body=summary或clean_text, use_tag),无第二道闸门。
4. **重新遇见接口:** `GET /api/feed/resurface` 取 core.notes 中 last_seen_at 最久/为空的 N 条,返回后更新其 last_seen_at。前端首页消费。
5. **搜索:** `GET /api/search?q=` 走 core.knowledge 的 body_tsv 全文检索。
6. **前端:** 详情页按 granularity 显示不同主操作——knowledge 显示"入脑",fragment 显示"存入收集箱";首页重新遇见卡片可当场"删除/入脑"。

**验收标准:**
- 一条 knowledge 类:review → 入脑 → `core.knowledge` 出现切块记录,`core.knowledge_tags` 挂上正确 theme/use 标签
- 一条 fragment(如"放低期待"):落 `core.notes`
- 首页重新遇见能刷出 notes 碎片,反复刷会轮换(last_seen_at 更新)
- 搜索关键词能命中 core.knowledge

---

## H. 五步之后(第二刀,先不做,列此备忘)

PDF 入口(pdftotext 抽取,复用第 3-5 步后半段)、长文连续截图拼接、**主题容器 core.topics**(从高频 topic 标签自然长出)、pgvector 语义检索、关联遇见、批量导入存量的限速队列 UI、language/life 等新入口、z-spanish 从 core 取料。

**批量导入存量提醒:** 5-6000 张历史图不要在初期一次性灌。先用五步做出的系统消化"每天约 50 张新增",养成使用习惯后,再把存量作为独立的限速慢跑任务处理。

---

## I. 待所有者确认的两个小决定(施工中遇到再定)

1. 重新遇见卡片:碎片推来时,除了"删除",要不要支持"当场提炼进核心脑"?(初版可先只支持看+删,提炼留详情页)
2. core.knowledge 切块粒度:初版按段落切即可;若某类内容希望更细(如像 z-spanish 那样的语义块),第二刀再定策略。

---

## 使用本手册的方式

打开 Claude Code,先让它读 `zbrain-architecture-v3.md` 全文,再贴本手册的【A. 启动说明】+【C. 第一步】,让它只做第一步。验收通过后,再贴【D. 第二步】……逐步推进。每步都在 iPhone 上真实用一下再往下走。
