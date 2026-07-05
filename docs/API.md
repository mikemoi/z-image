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
| GET | `` | `status/theme/use/granularity/promoted/deleted/limit/offset` 筛选 |
| GET | `/{id}` | 详情，含原图 checksum、OCR 与统一分类字段 |
| PATCH | `/{id}` | 修改 title/theme/use_tag/status/granularity/entry_type/domain/topics；人工改分类会锁定 AI 状态 |
| GET | `/review-queue?limit=10` | 集中批阅队列；支持 `entry_type/domain/use_tag` 分类筛选 |
| GET | `/review-facets` | 集中批阅未阅内容的类型、领域、用途计数 |
| GET | `/recommendations?limit=10` | 今日推荐队列；优先返回较久未看的截图 |
| POST | `/{id}/process` | 同步跑 Vision，调试用，会真实调用 AI |
| POST | `/{id}/reprocess` | 清 Vision 结果并回到 review |
| POST | `/{id}/insight` | 问问 AI；`refresh=true` 强制重算，否则使用缓存 |
| POST | `/{id}/adopt-theme` | 采纳旧 theme 生长建议 |
| GET | `/cleanup` | 返回 AI 判为无信息量的清库候选 |
| PATCH | `/{id}/review` | 标记已看 |
| PATCH | `/{id}/promote` | knowledge 切块进入 core.knowledge |
| POST | `/{id}/to-note` | fragment 进入 core.notes |
| PATCH | `/{id}/soft-delete` | 软删 |
| POST | `/{id}/restore` | 恢复 |
| DELETE | `/{id}/purge` | 永久删除 item；无其他引用时同时删原图 |

Item 的统一分类字段为 `entry_type/domain/use_tag/topics`；`highlights` 保存 AI 建议或人工确认的原文重点。来源在业务上固定为“截图”。旧 `theme/granularity` 仍保留。

## 文字入口 `/api/entries`

### 创建

`POST /api/entries`

```json
{
  "kind": "idea",
  "body": "转化，而不是惩罚。",
  "source_item_id": null,
  "entry_type": "句子",
  "domain": "方向",
  "use_tag": "心态",
  "topics": ["正向循环"],
  "highlights": ["转化，而不是惩罚。"]
}
```

`kind` 仅允许实际业务值 `idea/log/plan`（未知值当前会回退为 idea）。服务端忽略客户端来源推断：有 `source_item_id` 为“截图”，否则为“自己”。新建状态为 `filed`，分类为空时后台自动分类。

### 路由

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `` | 通用列表，支持 `kind/status/limit/offset` |
| GET | `/ideas` | 想法流，包含来源截图 checksum |
| GET | `/inbox` | 兼容旧 inbox 数据；当前创建流程不再产生 inbox |
| GET | `/plans` | pinned 计划 |
| GET | `/logs` | 日志时间线 |
| GET | `/logs/on-this-day` | 往年今天 |
| PATCH | `/{id}` | 修改正文或分类；分类字段人工修改后状态置 done |
| POST | `/{id}/promote` | 想法精选入 core.knowledge，重复调用返回 409 |
| POST | `/{id}/reclassify` | 清空四个分类字段并置 pending，供 Worker 重跑；不清除人工重点 |
| POST | `/{id}/file` | 兼容归位到 note/knowledge 的旧能力 |
| DELETE | `/{id}` | 移入回收站（软删除） |
| POST | `/{id}/restore` | 从回收站恢复 |
| DELETE | `/{id}/purge` | 永久删除已在回收站的 Entry |

Entry 响应包含：`entry_type/domain/use_tag/source/topics/highlights/ai_classify_status/ai_classified_at/ai_classify_output`，以及旧字段 `kind/theme/source_item_id`。

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
| GET | `/api/stats/dimensions` | 旧 theme/use 维度计数 |
| GET | `/api/stats/overview` | “我的 → 数据概览”；统一统计内容、类型、领域、用途、来源和分类状态 |
| GET | `/api/stats/theme-candidates` | 聚合旧 suggested_theme |
| POST | `/api/stats/theme-candidates/adopt` | 批量采纳旧 theme 候选 |
| GET | `/api/search?q=` | 搜索截图标题/摘要/OCR 与 Entry 正文 |
| GET | `/api/feed/resurface` | 轮换 core.notes |
| PATCH | `/api/feed/notes/{id}/soft-delete` | 软删碎片 |
| POST | `/api/feed/notes/{id}/restore` | 恢复碎片 |
| DELETE | `/api/feed/notes/{id}/purge` | 永久删除已软删碎片 |
| GET | `/api/trash` | 汇总回收站中的截图、Entry 和碎片 |
| GET | `/api/files/{checksum}` | 鉴权读取原图；磁盘文件丢失返回 410 |

交互式 OpenAPI：`http://127.0.0.1:8000/docs`。
