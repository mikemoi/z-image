# zbrain API 参考

> 当前实现(v0.3)的完整端点清单。除 `/api/health` 外,所有 `/api/*` 均需鉴权:
> `Authorization: Bearer <AUTH_TOKEN>`(也接受不带 `Bearer` 前缀的裸 token)。
> 路由源码:[`backend/routers/`](../backend/routers/) + [`backend/main.py`](../backend/main.py)。

## 系统 / 鉴权(main.py)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 探活 + DB 连通性(**免鉴权**):`{status, db}` |
| GET | `/api/whoami` | 验证 token 通路 |
| GET | `/api/worker/status` | 当日 Vision 预算:`{date, used, limit, pending, working}`(前端只用 `working` 布尔,不显示数字) |

## 条目 items(`/api/items`)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/upload` | 批量上传(multipart `images[]`)。逐张 checksum 去重、落盘、`items(status=review)`,**同步返回** `{received, message}`,不等 AI |
| GET | `` | 列表筛选:`?status=&theme=&use=&granularity=&deleted=false&limit=50&offset=0` → `{total, limit, offset, items[]}` |
| GET | `/{id}` | 详情:原图 checksum + 标签 + summary + clean_text/raw_text |
| PATCH | `/{id}` | 改标签:`{title?, theme?, use_tag?, status?, granularity?}`(只更传入字段) |
| POST | `/{id}/process` | 同步跑一遍 Vision(调试用),完成返回详情 |
| POST | `/{id}/reprocess` | 清结果、重置 review,让 worker 重跑 |
| POST | `/{id}/insight` | **问问 AI**:`?refresh=true` 强制重算。返回 `{explanation, quality, quality_note, suggested_theme, suggested_theme_reason, cached}`;结果缓存进 `ai_insight` |
| POST | `/{id}/adopt-theme` | 采纳 AI 提议的新分类:`{theme}` → 建 tag + 归入,返回详情 |
| GET | `/cleanup` | 清库:列出 `ai_output.quality='无信息量'` 的条目 `{id, checksum, title, summary, quality_note}[]` |
| PATCH | `/{id}/review` | 闸门一:标记已看 |
| PATCH | `/{id}/promote` | 闸门二(knowledge):切块入 `core.knowledge` + 打 theme/use 标签(需先 review;asset 拒绝) |
| POST | `/{id}/to-note` | 碎片(fragment)落 `core.notes`(轻路径,无第二闸门;asset 拒绝) |
| PATCH | `/{id}/soft-delete` | 软删入回收站 |
| POST | `/{id}/restore` | 从回收站恢复 |
| DELETE | `/{id}/purge` | 彻底销毁:删记录 + 抹磁盘原文件(仅当无其他 item 引用该 file) |

## 文字入口 entries(`/api/entries`,v0.3)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `` | 记一条:`{kind, body, mood?, logged_for?, pinned?}`。log 缺省日期=今天;log/plan 直接 `filed`,note/clip 进 `inbox` |
| GET | `` | 列表:`?kind=&status=&limit=&offset=` |
| GET | `/inbox` | 待整理(status=inbox 的 note/clip) |
| GET | `/plans` | 钉住的计划(kind=plan, pinned) |
| GET | `/logs` | 日志时间线(按 logged_for 倒序) |
| GET | `/logs/on-this-day` | 往年今天(同月日、往年的日志) |
| PATCH | `/{id}` | 改:`{body?, mood?, pinned?, status?, logged_for?}` |
| POST | `/{id}/file` | 归位:`{target: 'note'\|'knowledge'}` → 写入 core + status=filed(建 sources 指向本 entry) |
| PATCH | `/{id}/soft-delete` | 软删 |
| POST | `/{id}/restore` | 恢复 |

## 维度 / 生长分类 stats(`/api/stats`)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/dimensions` | 维度计数:`{total, assets, themes{}, uses{}}` |
| GET | `/theme-candidates` | 新分类候选:`?min=3` → `[{name, count}]`(suggested_theme 攒够阈值、未采纳的) |
| POST | `/theme-candidates/adopt` | 批量采纳一簇:`{theme}` → 建 tag + 整簇归入,返回 `{theme, count}` |

## 搜索 search(`/api/search`)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `` | 全文检索:`?q=&limit=50`。覆盖截图条目 + 手写文字,返回 `SearchHit[]`(`source` 区分 image/entry) |

## 重新遇见 feed(`/api/feed`)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/resurface` | 取 `last_seen_at` 最久/为空的碎片 `?limit=5`,返回后更新其 last_seen_at 轮换 |
| PATCH | `/notes/{id}/soft-delete` | 删掉一条碎片,以后不再遇见 |

## 原图 files(`/api/files`)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/{checksum}` | 按 checksum 返回磁盘原图(inline);记录在但磁盘丢 → 410 |

---

## 鉴权与配置

- 单用户 header token(`backend/auth.py`),token 来自环境变量 `AUTH_TOKEN`。
- 配置项(`backend/config.py`):`DATABASE_URL` `AUTH_TOKEN` `FILES_ROOT` `OPENROUTER_API_KEY` `OPENROUTER_BASE_URL` `VISION_MODEL` `VISION_DAILY_BUDGET` `VISION_MAX_ATTEMPTS` `WORKER_POLL_SECONDS`。
- 交互式 API 文档(FastAPI 自带):`http://<host>:8000/docs`。
