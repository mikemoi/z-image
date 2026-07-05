# 下一步交接记录：最终内容坐标与重新整理

> 写于 2026-07-06。  
> 这份文件是给下一位接手助手/工程师看的“未开工需求 + 当前工作区状态”。
> 注意：本文件记录的是用户最新确认方向，不代表当前源码已经全部实现。

---

## 0. 当前工作区状态

当前分支：`main`。

当前工作区有一批未提交改动，主要来自上一轮“统一分类一致性”的中间版：

- Browse 从旧 `theme/use` 改成新分类浏览。
- 截图卡片、详情页、批阅页改为统一分类展示组件。
- 前端移除了旧 `themeCandidates/adoptTheme` 主线调用。
- 后端 `items` 列表增加了 `entry_type/domain/main_topic/tag/source` 筛选。
- 后端 entries/items 的人工更新增加了最终组合校验。
- 文档中部分“主主题/相关主题”被改成“主轴/关联”。
- 验证曾通过：
  - `backend`: `python -m unittest discover -s tests -v`
  - `backend`: `python -m compileall -q .`
  - `frontend`: `npm run build`

但是：用户随后给了“最终稳定版”需求，要求从「主轴」改为「主题」，并新增 `sub_topic`、候选机制、重新整理、时间线、搜索范围等。  
因此当前未提交改动不能直接视为最终完成版，下一位应在这些未提交改动基础上继续调整，或先整理为一个清晰提交再继续。

---

## 1. 用户最新最终分类体系

最终内容坐标顺序：

```text
内容坐标
├── 类型：想法 / 知识 / 资料 / 记录 / 规则
├── 领域：身心 / 生活 / 能力 / 财务 / 方向
├── 主题：领域下固定主题
├── 子题：主题下固定细分
├── 相关：最多 2 个相关主题
├── 标签：细节关键词
└── 来源：我 / 图片 / 文件
```

一句话原则：

```text
类型看形态。
领域定大区。
主题定方向。
子题定具体位置。
相关处理交叉。
标签补充细节。
来源看内容从哪里来。
```

前端卡片统一显示：

```text
[类型] [领域] [主题] [子题]
相关：xxx / xxx
#标签1 #标签2 #标签3
来源：我 / 图片 / 文件
```

---

## 2. 不要做的事

明确不要：

- 不新增 `ownership` 字段。
- 不删除旧字段。
- 不破坏旧数据。
- 不破坏上传、OCR、浏览、详情、搜索、想法、日志。
- 不恢复“用途”作为一级字段。
- 不让 AI 自动新增类型、领域、主题、子题、来源。
- 不让 AI 直接创建正式标签或正式子题。
- 不默认覆盖用户手动修正的分类。
- 不做复杂知识图谱。
- 不做向量搜索。

旧字段继续保留兼容：

```text
kind
theme
use_tag
granularity
topics
source_item_id
highlights
promoted_at
```

重新整理不要处理：

```text
body
title
summary
OCR 原文
图片
文件
highlights
promoted_at
source_item_id
theme
use_tag
granularity
topics
```

重点句 `highlights` 不需要 AI 介入；重新整理不要生成、不要更新 highlights。

---

## 3. source 来源最终规则

最终 `source` 固定值：

```text
我
图片
文件
```

旧值映射：

```text
自己 → 我
截图 → 图片
文件 → 文件
```

关键原则：

- `source = 内容本身从哪里来`
- `source_item_id = 如果这条想法关联了某张图片，就保留图片关联`

特别注意：

```text
我在图片详情页写“这张图提醒我……”
这条正文是我写的，所以：
source = 我
entry_type = 想法
source_item_id = 对应图片 id
```

不要再把“图片详情页写的想法”标成 `source=图片`。

搜索范围只做前端/API筛选名，不做数据库字段：

```text
我的 = source = 我
外部 = source IN ('图片', '文件')
全部 = 不限制 source
```

---

## 4. entry_type 类型压缩

最终只保留 5 个：

```text
想法
知识
资料
记录
规则
```

旧值映射：

```text
句子 → 想法
决策 → 规则
想法 → 想法
知识 → 知识
资料 → 资料
记录 → 记录
规则 → 规则
```

解释：

- 想法 = 我的理解、判断、感悟、句子、认知沉淀
- 知识 = 外部经验、教程、解释、可学习内容
- 资料 = 合同、证件、药盒、票据、配置、需要留存的材料
- 记录 = 我的时间线、状态、情绪、用药、运动、睡眠
- 规则 = 我的底线、决策、行为准则、不做清单

要求：

- 前端下拉框只显示 5 个类型。
- 后端 Literal / normalize 只允许 5 个类型。
- 旧数据里的“句子”显示和重新整理时映射为“想法”。
- 旧数据里的“决策”显示和重新整理时映射为“规则”。

---

## 5. 领域与主题固定表

领域固定：

```text
身心
生活
能力
财务
方向
```

主题必须属于领域：

```text
身心：ADHD / 情绪 / 药物 / 运动 / 睡眠 / 身体
生活：马德里 / 居住 / 证件 / 合同 / 关系 / 日常
能力：西班牙语 / AI / 编程 / 服务器 / 产品 / 学习
财务：债务 / 收入 / 消费 / 投资 / 房产 / 交易
方向：目标 / 底线 / 规则 / 决策 / 复盘 / 正向循环
```

规则：

- `main_topic` 单选。
- `main_topic` 必须属于 `domain`。
- AI 不能新增 `main_topic`。

---

## 6. 新增 sub_topic 子题

新增字段：

```text
sub_topic
```

规则：

- `sub_topic` 是主题下面的固定细分。
- `sub_topic` 单选。
- `sub_topic` 可以为空。
- AI 不能自由新增子题。
- 如果没有合适子题，使用 `未细分`。
- `sub_topic` 必须属于当前 `main_topic`。

原则：

```text
主题和子题是骨架。
标签只是细节关键词。
标签不能代替子题。
```

需要在前后端统一维护完整 `SUB_TOPICS_BY_TOPIC` 固定表。用户提供了完整初版，见附件：

```text
C:\Users\momol\.codex\attachments\711e466e-bb98-40d0-ba49-0528aa583d80\pasted-text.txt
```

实现时不要遗漏这些大类：

- 身心：ADHD / 情绪 / 药物 / 运动 / 睡眠 / 身体
- 生活：马德里 / 居住 / 证件 / 合同 / 关系 / 日常
- 能力：西班牙语 / AI / 编程 / 服务器 / 产品 / 学习
- 财务：债务 / 收入 / 消费 / 投资 / 房产 / 交易
- 方向：目标 / 底线 / 规则 / 决策 / 复盘 / 正向循环

每个主题下都必须包含 `未细分`。

---

## 7. related_topics 相关

字段仍为：

```text
related_topics
```

前端中文显示：

```text
相关
```

规则：

- 最多 2 个。
- 从固定主题表里选。
- 可以跨领域。
- 不能重复。
- 不能包含 `main_topic`。
- 仍然是“主题级别”，不是子题级别。
- 不要新增 `related_sub_topics`。

---

## 8. 候选标签 / 候选子题机制必须做

用户补充明确：候选机制是需要的。

原因：

- 已经上传过很多 OCR 图片内容。
- 历史 OCR / 图片内容没有走最终分类体系。
- 需要通过“重新整理”让 AI 后台重新分类。
- 新版固定子题和标签可能覆盖不全，所以 AI 要能提名候选，但不能直接污染正式体系。

AI 不能直接新增正式标签或正式子题。

AI 可以提出：

```text
candidate_tags
candidate_sub_topic
```

候选标签：

- 字段：`candidate_tags`
- 只进入候选池。
- 不直接变成正式 `tags`。
- 同一个候选标签出现 >= 5 条后，进入 `我的 / 待审批`。

候选子题：

- 字段：`candidate_sub_topic`
- 必须带建议位置：`domain / main_topic`
- 不直接变成正式 `sub_topic`
- 同一个候选子题在同一个 `main_topic` 下出现 >= 5 条后，进入 `我的 / 待审批`。

用户操作：

```text
批准
合并到已有标签 / 子题
忽略
```

建议新增候选表：

```sql
CREATE TABLE IF NOT EXISTS core.classification_candidates (
  id BIGSERIAL PRIMARY KEY,
  candidate_type TEXT NOT NULL, -- tag / sub_topic
  name TEXT NOT NULL,
  domain TEXT,
  main_topic TEXT,
  status TEXT NOT NULL DEFAULT 'pending', -- pending / active / ignored / merged
  target_name TEXT,
  occurrence_count INTEGER NOT NULL DEFAULT 0,
  content_count INTEGER NOT NULL DEFAULT 0,
  examples JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

也可以拆成候选项表 + occurrence 表，但第一版建议保持简单。

---

## 9. 我的 / 待审批

候选机制统一放在「我的」页面。

新增入口：

```text
待审批
```

不要分散成“待批准标签页面”和“待批准子题页面”。

「我的 / 待审批」统一展示：

1. 候选标签
2. 候选子题
3. 以后可能扩展的其他候选项

第一版至少支持：

候选标签：

```text
candidate_tag
出现次数
关联内容数量
建议领域 / 主题
操作：批准 / 合并 / 忽略
```

候选子题：

```text
candidate_sub_topic
建议位置：domain / main_topic
出现次数
关联内容数量
操作：批准 / 合并 / 忽略
```

默认阈值：

```text
同一候选出现 >= 5 条
```

建议接口：

```text
GET /api/candidates
POST /api/candidates/{id}/approve
POST /api/candidates/{id}/merge
POST /api/candidates/{id}/ignore
```

---

## 10. 我的 / 重新整理

用户最后修正：重新整理功能只需要一个主按钮：

```text
重新整理全部分类
```

不要做多个按钮。

点击后：

1. 先做确定性修正：

```text
source 旧值映射：
自己 → 我
截图 → 图片
文件 → 文件

entry_type 旧值映射：
句子 → 想法
决策 → 规则

related_topics 去重、最多 2 个
tags 去重、最多 5 个
非法 sub_topic 改为 未细分
```

2. 然后把历史内容重新排队：

```text
core.entries 设置 ai_classify_status = pending
image.items 设置 ai_classify_status = pending
```

3. 后台 worker 慢慢让 AI 重新分类。

要求：

- 不同步调用大量 AI。
- 不卡住页面。
- 不覆盖用户正文/OCR/图片/文件/highlights/promoted_at/source_item_id/旧字段。

建议接口：

```text
POST /api/admin/reclassify-all
```

返回：

```json
{
  "ok": true,
  "queued_entries": 120,
  "queued_items": 630
}
```

---

## 11. AI 重新整理处理字段

AI 重新整理时只处理：

```text
entry_type
domain
main_topic
sub_topic
related_topics
tags
ai_classify_status
ai_classified_at
ai_classify_output
candidate_tags
candidate_sub_topic
```

`source` 不让 AI 猜，只做确定性修正。

不要处理：

```text
body
title
summary
OCR 原文
图片
文件
highlights
promoted_at
source_item_id
theme
use_tag
granularity
topics
```

AI 输出建议：

```json
{
  "entry_type": "想法",
  "domain": "身心",
  "main_topic": "情绪",
  "sub_topic": "调节",
  "related_topics": ["运动"],
  "tags": ["正向循环", "自我调节"],
  "candidate_tags": ["行动转化"],
  "candidate_sub_topic": null,
  "candidate_sub_topic_domain": null,
  "candidate_sub_topic_main_topic": null
}
```

注意：新版重新整理不要再生成或更新 `highlights`。

---

## 12. 我的 / 时间线

新增入口：

```text
时间线
```

用途：

```text
查看某一天的记录。
```

记录入口创建 log 时：

```text
kind = log
entry_type = 记录
source = 我
```

如果 `logged_for` 为空，自动设置为 Europe/Madrid 当天日期。

新增接口：

```text
GET /api/entries/timeline?date=YYYY-MM-DD
```

没有 `date` 时默认今天。

查询逻辑：

```sql
WHERE kind = 'log'
  AND source = '我'
  AND deleted_at IS NULL
  AND logged_for = :date
ORDER BY created_at ASC
```

页面显示：

```text
时间
正文
简要分类
编辑
删除
```

---

## 13. 搜索范围

搜索页面增加范围筛选：

```text
全部
我的
外部
```

默认：

```text
全部
```

规则：

```text
我的 = source = 我
外部 = source IN ('图片', '文件')
全部 = 不限制 source
```

“外部”只是筛选名称，不是数据库字段。

搜索结果卡片也应显示统一内容坐标：

```text
[类型] [领域] [主题] [子题]
相关：xxx / xxx
#标签
来源：我 / 图片 / 文件
```

---

## 14. 我的页面最终结构

用户最终要求：

```text
我的
├── 数据概览
├── 时间线
├── 重新整理
├── 待审批
└── 分类说明 / 设置
```

不要单独做“待批准标签页面”和“待批准子题页面”。

---

## 15. 数据库迁移清单

需要在 `backend/db.py::ensure_schema()` 和 `deploy/init.sql` 中补齐：

```sql
ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS sub_topic TEXT;
ALTER TABLE image.items ADD COLUMN IF NOT EXISTS sub_topic TEXT;
```

确认 `image.items.source` 默认：

```sql
source TEXT DEFAULT '图片'
```

候选表：

```sql
CREATE TABLE IF NOT EXISTS core.classification_candidates (...);
```

不新增 `ownership`。

---

## 16. 前端涉及文件

预计会改：

```text
frontend/src/classification.js
frontend/src/api.js
frontend/src/App.jsx
frontend/src/components/ClassificationGuide.jsx
frontend/src/components/ClassificationMeta.jsx
frontend/src/components/EntryEditor.jsx
frontend/src/components/ItemCard.jsx
frontend/src/pages/Browse.jsx
frontend/src/pages/Detail.jsx
frontend/src/pages/Ideas.jsx
frontend/src/pages/Logs.jsx
frontend/src/pages/Me.jsx
frontend/src/pages/Search.jsx
frontend/src/pages/Overview.jsx
frontend/src/pages/ReviewSession.jsx
```

预计新增：

```text
frontend/src/pages/Reclassify.jsx
frontend/src/pages/Approvals.jsx
frontend/src/pages/Timeline.jsx
```

---

## 17. 后端涉及文件

预计会改：

```text
backend/classify.py
backend/db.py
backend/worker.py
backend/models/entries.py
backend/models/items.py
backend/routers/entries.py
backend/routers/items.py
backend/routers/search.py
backend/routers/stats.py
backend/main.py
backend/tests/test_classification.py
```

预计新增：

```text
backend/routers/admin.py
backend/routers/candidates.py
```

---

## 18. 风险点

1. 当前工作区已有未提交的“中间版分类一致性”改动，下一位不能直接当最终版提交。
2. 用户最新稳定版从“主轴”改回“主题”，还新增“子题”；需统一改掉中间版用词。
3. source 语义变化很重要：图片详情页写的想法仍然是 `source=我`，不能再用 `source_item_id` 推断为图片。
4. 重新整理会把大量历史内容设为 pending，必须只排队，不同步调用 AI。
5. highlights 不参与重新整理，避免覆盖用户人工重点。
6. 候选机制要防止 AI 直接污染正式 tags/sub_topic。
7. 子题表很长，前后端必须保持一致，否则会出现编辑保存失败或 AI 输出被 normalize 掉。

---

## 19. 下一位建议执行顺序

1. 先整理当前未提交 diff，决定是继续改还是先临时提交中间版。
2. 把“主轴”统一改回“主题”，加入 `sub_topic`。
3. 压缩 `entry_type` 和 `source`。
4. 实现固定子题表与 normalize 校验。
5. 更新 worker/classify prompt，不再生成 highlights。
6. 实现重新整理排队接口和页面。
7. 实现候选表、候选写入、待审批页面。
8. 实现时间线接口和页面。
9. 实现搜索范围筛选。
10. 全量验证：
    - 后端单测
    - 后端 compileall
    - 前端 build
    - 本地 API smoke test

