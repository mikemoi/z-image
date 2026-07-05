# zbrain API 参考

> 当前源码基线。所有 `/api/*`（除 health）需要 `Authorization: Bearer <AUTH_TOKEN>`。

## 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 免鉴权；返回服务和数据库状态 |
| GET | `/api/whoami` | 验证 token |
| GET | `/api/worker/status` | 当日三条 AI 管线共享的进程内预算及工作状态 |

## 截图条目 `/api/items`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/upload` | multipart `images[]`；落盘和建 item 后立即返回，不等 AI |
| GET | `` | 支持 `entry_type/domain/main_topic/tag/source` 新分类筛选；`status/theme/use/granularity/deleted/limit/offset` 仅兼容旧链路 |
| GET | `/{id}` | 详情，含原图 checksum、OCR 与统一分类字段 |
| PATCH | `/{id}` | 修改新分类字段；旧 theme/use_tag/topics 继续兼容 |
| GET | `/review-queue?limit=10` | 集中批阅队列；支持 `entry_type/domain/main_topic/tag/source` 筛选 |
| GET | `/review-facets` | 集中批阅未阅内容的类型、领域、主轴、来源、标签计数 |
| POST | `/{id}/reclassify` | 只重跑统一分类，不重跑 OCR，保留人工重点 |
| GET | `/recommendations?limit=10` | 今日推荐队列；优先返回较久未看的截图 |
| POST | `/{id}/process` | 同步跑 Vision，调试用，会真实调用 AI |
| POST | `/{id}/reprocess` | 清 Vision 结果并回到 review |
| POST | `/{id}/insight` | 问问 AI；`refresh=true` 强制重算，否则使用缓存 |
| POST | `/{id}/adopt-theme` | 兼容旧 theme 生长建议；当前页面主线不再使用 |
| GET | `/cleanup` | 返回 AI 判为无信息量的清库候选 |
| PATCH | `/{id}/review` | 标记已看 |
| PATCH | `/{id}/promote` | knowledge 切块进入 core.knowledge |
| POST | `/{id}/to-note` | fragment 进入 core.notes |
| PATCH | `/{id}/soft-delete` | 软删 |
| POST | `/{id}/restore` | 恢复 |
| DELETE | `/{id}/purge` | 永久删除 item；无其他引用时同时删原图 |

Item 的统一分类字段为 `entry_type/domain/main_topic/sub_topic/related_topics/tags/source`；`source` 为 `我/图片/文件`，截图默认为 `图片`；`highlights` 保存人工重点。旧 `theme/use_tag/topics/granularity` 仍保留兼容。

## 文字入口 `/api/entries`

### 创建

`POST /api/entries`

```json
{
  "kind": "idea",
  "body": "转化，而不是惩罚。",
  "source_item_id": null,
  "entry_type": "想法",
  "domain": "方向",
  "main_topic": "规则",
  "sub_topic": "不做清单",
  "related_topics": ["正向循环"],
  "tags": ["心态"],
  "highlights": ["转化，而不是惩罚。"]
}
```

`kind` 仅允许实际业务值 `idea/log/plan`（未知值当前会回退为 idea）。服务端统一写 `source=我`；`source_item_id` 只表示关联图片，不改变来源。`kind=idea` 默认 `entry_type=想法`，`kind=log` 默认 `entry_type=记录`。新建状态为 `filed`，分类为空时后台自动分类。

### 路由

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `` | 通用列表，支持 `kind/status/limit/offset` |
| GET | `/ideas` | 想法流，包含来源截图 checksum |
| GET | `/inbox` | 兼容旧 inbox 数据；当前创建流程不再产生 inbox |
| GET | `/plans` | pinned 计划 |
| GET | `/logs` | 日志时间线 |
| GET | `/logs/on-this-day` | 往年今天 |
| GET | `/timeline?date=YYYY-MM-DD` | 某一天的记录；默认 Europe/Madrid 今天，按 created_at 正序 |
| PATCH | `/{id}` | 修改正文或分类；分类字段人工修改后状态置 done |
| POST | `/{id}/promote` | 想法精选入 core.knowledge，重复调用返回 409 |
| POST | `/{id}/reclassify` | 清空新分类字段并置 pending；旧字段和人工重点不清除 |
| POST | `/{id}/file` | 兼容归位到 note/knowledge 的旧能力 |
| DELETE | `/{id}` | 移入回收站（软删除） |
| POST | `/{id}/restore` | 从回收站恢复 |
| DELETE | `/{id}/purge` | 永久删除已在回收站的 Entry |

Entry 响应包含：`entry_type/domain/main_topic/sub_topic/related_topics/tags/source/highlights/ai_classify_status/ai_classified_at/ai_classify_output`，以及旧字段 `kind/theme/use_tag/topics/source_item_id`。

## 维护 `/api/admin` 与候选 `/api/candidates`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/admin/reclassify` | 只排队重新整理分类，不同步调用 AI；`scope=all/mine/external/unclassified/entries/items`，`mode=fill_missing/force` |
| GET | `/api/candidates` | 查看出现次数达到阈值的候选标签/候选子题 |
| POST | `/api/candidates/{id}/approve` | 批准候选 |
| POST | `/api/candidates/{id}/merge` | 合并到已有名称 |
| POST | `/api/candidates/{id}/ignore` | 忽略候选 |

## 设置 `/api/settings`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/settings` | 返回 ocr/insight/classify 三个当前模型及候选列表 |
| PUT | `/api/settings` | 更新任意模型；写入 core.settings 后即时生效 |

```json
{"ocr_model":"openai/gpt-4.1-mini","insight_model":"openai/gpt-4.1","classify_model":"openai/gpt-4.1-mini"}
```

## 其他

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/stats/dimensions` | 兼容旧 theme/use 维度计数；当前统计主线用 overview |
| GET | `/api/stats/overview` | “我的 → 数据概览”；统计内容、类型、领域、主轴、来源和分类状态 |
| GET | `/api/stats/theme-candidates` | 兼容旧 suggested_theme 聚合；当前页面主线不再使用 |
| POST | `/api/stats/theme-candidates/adopt` | 兼容旧 theme 候选批量采纳 |
| GET | `/api/search?q=&scope=all` | 搜索截图标题/摘要/OCR 与 Entry 正文；`scope=all/mine/external` |
| GET | `/api/feed/resurface` | 轮换 core.notes |
| PATCH | `/api/feed/notes/{id}/soft-delete` | 软删碎片 |
| POST | `/api/feed/notes/{id}/restore` | 恢复碎片 |
| DELETE | `/api/feed/notes/{id}/purge` | 永久删除已软删碎片 |
| GET | `/api/trash` | 汇总回收站中的截图、Entry 和碎片 |
| GET | `/api/files/{checksum}` | 鉴权读取原图；磁盘文件丢失返回 410 |

交互式 OpenAPI：`http://127.0.0.1:8000/docs`。
