# zbrain 数据库结构 · 数据字典

> 反映当前实现(v0.3)的真实 schema。建表见 [`deploy/init.sql`](../deploy/init.sql),
> 运行时增量迁移见 [`backend/db.py`](../backend/db.py) 的 `ensure_schema()`。
> 命名约定:全小写下划线;主键 `id`;外键 `<单数表>_id`;时间戳 `_at`;布尔 `is_`。

数据库名 `zbrain`,两个 schema:

- **`core`** — 脑本体,跨入口的核心资产(知识/碎片/标签/来源/手写文字)
- **`image`** — z-image 入口,截图的文件/条目/文字三层

磁盘原图:`/data/zbrain/files/image/<checksum>.<ext>`(数据库只存路径,不存二进制)。

---

## 枚举值速查(先看这个,后面字段会引用)

| 用在哪 | 值 | 含义 |
|---|---|---|
| `image.items.status` | `review` | 待处理/等人工兜底(默认) |
| | `ok` | AI 已处理完 |
| | `archive` | 归档(暂未大量使用) |
| | `useless` | 无信息量(可配合清库) |
| `image.items.granularity` | `knowledge` | 成体系知识,走两道闸门入 `core.knowledge` |
| | `fragment` | 孤立金句/感悟,走轻路径入 `core.notes` |
| | `asset` | 证件/票据/二维码等"要用时查"的资料凭证,不入脑 |
| `theme`(主题) | `trading` `ai` `adhd` `language` `life` `other` | 预置六类;**可生长**(用户采纳 AI 建议后新增,如"运动") |
| 统一类型 | `想法` `句子` `规则` `决策` `知识` `资料` `记录` | 内容是什么 |
| 统一领域 | `身心` `生活` `能力` `财务` `方向` | 固定大领域 |
| `main_topic` | 各领域固定六个主题 | 主轴，单选且必须属于 domain |
| `related_topics` | JSONB 固定主轴数组 | 关联，最多 2 个 |
| `tags` | JSONB 字符串数组 | 细节标签，最多 5 个；“他人经验”属于标签 |
| `use_tag/topics` | 旧字段 | 仅兼容保留，不再作为新分类核心 |
| `source` | `自己` `截图` `文件` | 进入方式，不表示可信度 |
| `quality`(AI 质量判断) | `干货` `反面样本` `无信息量` | 反面样本=像鸡汤但有避坑价值,仍值得留;只有无信息量建议清 |
| `core.tags.kind` | `theme` `use` `topic` | 标签种类;topic 为自由细分(预留) |
| `core.entries.kind` | `idea` `log` `plan` | 想法 / 日志 / 计划入口 |
| `core.entries.status` | `inbox` `filed` | inbox 仅兼容旧数据；当前创建 filed |
| `ai_classify_status` | `pending` `done` `failed` | 待分类 / 完成或人工锁定 / 失败待手动重跑 |
| `image.contents.extraction_method` | `vision` `pdftotext` `ocr` | 文字提取方式(当前只用 vision) |
| `image.contents.cleaning_method` | `rules` `ai` `rules+ai` | 清洗方式(当前 rules) |

---

## core schema — 脑本体

### `core.sources` — 来源登记
每条进入 core 的知识/碎片都登记一个来源,可回溯它从哪来(截图 or 手写文字)。

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `origin_schema` | TEXT NOT NULL | 来源 schema:`image`(截图)或 `core`(手写 entries) |
| `origin_table` | TEXT NOT NULL | 来源表:`files` 或 `entries` |
| `origin_id` | BIGINT NOT NULL | 来源行 id(→ `image.files.id` 或 `core.entries.id`) |
| `created_at` | TIMESTAMPTZ | 创建时间 |

### `core.knowledge` — 精选脑(成体系知识块)
两道闸门 + 全文检索。将来接 pgvector 做语义检索(`embedding` 列现预留不建)。

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `source_id` | BIGINT FK→sources | 来源(可空) |
| `title` | TEXT | 原文标题/问题(如"一个人最根本的能力是什么"),可空 |
| `body` | TEXT NOT NULL | 知识块正文(从 clean_text 切块或来自手写) |
| `seq` | INT | 同一来源切成多块时的顺序 |
| `summary` | TEXT | 摘要 |
| `deleted_at` | TIMESTAMPTZ | 软删时间;NULL=未删 |
| `body_tsv` | tsvector GENERATED | `to_tsvector('simple', title+body)` 自动生成,GIN 索引全文检索 |
| `created_at` | TIMESTAMPTZ | 创建时间 |

索引:`idx_knowledge_tsv`(GIN body_tsv)、`idx_knowledge_deleted`。

### `core.notes` — 感悟收集箱(万金油碎片)
低门槛(无第二道闸门),靠"重新遇见"轮换激活,不混进精选脑避免稀释。

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `source_id` | BIGINT FK→sources | 来源(可空,手敲的没有) |
| `body` | TEXT NOT NULL | 碎片正文(如"放低期待,接受度就高了") |
| `use_tag` | TEXT | 用途(心态/避坑/灵感居多) |
| `last_seen_at` | TIMESTAMPTZ | 上次"重新遇见"推送时间,支持轮换;NULL=从没遇见(优先推) |
| `deleted_at` | TIMESTAMPTZ | 软删 |
| `created_at` | TIMESTAMPTZ | 创建时间 |

索引:`idx_notes_lastseen`、`idx_notes_deleted`。

### `core.tags` — 双维度 + 自由细分标签

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `name` | TEXT NOT NULL | 标签名(如 `trading`、`方法`、`运动`) |
| `kind` | TEXT NOT NULL | `theme`/`use`/`topic` |
| — | UNIQUE(name,kind) | 同名同种只一条 |

预置 11 条:6 theme + 5 use(见枚举表)。theme 可通过"采纳新分类"生长。

### `core.knowledge_tags` — 知识↔标签多对多

| 字段 | 类型 | 含义 |
|---|---|---|
| `knowledge_id` | BIGINT FK→knowledge ON DELETE CASCADE | |
| `tag_id` | BIGINT FK→tags ON DELETE CASCADE | |
| — | PK(knowledge_id, tag_id) | 组合主键 |

### `core.entries` — 文字入口
想法、日志、计划共用一张表。`kind` 表示入口，不等于内容类型 `entry_type`。

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `kind` | TEXT NOT NULL | 当前业务值 `idea`/`log`/`plan` |
| `body` | TEXT NOT NULL | 文字内容 |
| `status` | TEXT NOT NULL DEFAULT 'inbox' | 兼容旧数据；当前创建统一写 `filed` |
| `mood` | TEXT | 日志可选心情(emoji) |
| `pinned` | BOOLEAN DEFAULT false | 计划钉住(常驻首页) |
| `logged_for` | DATE | 日志的"事情发生日期",缺省=今天 |
| `source_item_id` | BIGINT | 来自截图详情页时关联 item；当前未设 FK |
| `theme` | TEXT | 旧主题字段，兼容保留 |
| `promoted_at` | TIMESTAMPTZ | 想法精选入脑时间 |
| `entry_type` | TEXT | 类型：想法/句子/规则/决策/知识/资料/记录 |
| `domain` | TEXT | 领域：身心/生活/能力/财务/方向 |
| `main_topic` | TEXT | 对应领域下的固定主轴 |
| `related_topics` | JSONB | 关联数组，最多 2 个 |
| `tags` | JSONB | 细节标签数组，最多 5 个 |
| `use_tag` | TEXT | 旧用途字段，兼容保留 |
| `source` | TEXT | 自己/截图/文件；创建时由服务端推断 |
| `topics` | JSONB | 旧标签字段，兼容保留 |
| `highlights` | JSONB | 重点原句数组；人工结果优先，AI 不覆盖已有值 |
| `ai_classify_status` | TEXT DEFAULT pending | pending/done/failed；failed 不自动重试 |
| `ai_classified_at` | TIMESTAMPTZ | 自动分类成功时间 |
| `ai_classify_output` | JSONB | 分类器规整结果与原始返回 |
| `deleted_at` | TIMESTAMPTZ | 软删 |
| `created_at` / `updated_at` | TIMESTAMPTZ | 创建/更新时间 |

索引:`idx_entries_kind`、`idx_entries_status`、`idx_entries_logged`、`idx_entries_deleted`。

自动分类只处理分类为空且状态为 NULL/pending 的记录。人工修改分类会把状态置 done；reclassify 会清空分类并重新置 pending。

---

## image schema — z-image 入口

### `image.files` — 第一层:不可变事实源
只增不改。用户删手机后,磁盘原图是唯一副本。

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `file_path` | TEXT NOT NULL | 磁盘绝对/相对路径 |
| `file_type` | TEXT NOT NULL | `image`(或将来 `pdf`) |
| `original_filename` | TEXT NOT NULL | 上传时原始文件名 |
| `checksum` | TEXT NOT NULL | sha256,去重底子;也是取图 URL 的 key |
| `file_size` | BIGINT | 字节数 |
| `created_at` | TIMESTAMPTZ | 落盘时间 |

索引:`idx_files_checksum`。一个 file 可被多个 item 引用(同图重复上传复用 file 行)。

### `image.items` — 第二层:条目(处理状态 + 双维度 + 闸门)

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `file_id` | BIGINT FK→files NOT NULL | 对应原图 |
| `status` | TEXT NOT NULL DEFAULT 'review' | 处理路径:review/ok/archive/useless |
| `title` | TEXT | 原文标题/问题,可空 |
| `summary` | TEXT | 一句话摘要;图解/资料类是唯一检索抓手 |
| `theme` | TEXT | 主题(见枚举) |
| `use_tag` | TEXT | 用途(见枚举) |
| `granularity` | TEXT | knowledge/fragment/asset |
| `is_ocr_suitable` | BOOLEAN DEFAULT false | 是否值得入库正文(两段式省钱的判断) |
| `ai_output` | JSONB | AI 自动处理的完整结构化输出(见下方结构) |
| `ai_insight` | JSONB | 「问问 AI」按需生成的看法缓存(v0.3,见下方结构) |
| `entry_type` | TEXT | 统一分类类型 |
| `domain` | TEXT | 统一分类领域 |
| `main_topic` | TEXT | 固定主轴 |
| `related_topics` | JSONB | 关联数组，最多 2 个 |
| `tags` | JSONB | 细节标签数组，最多 5 个 |
| `source` | TEXT | 默认截图 |
| `topics` | JSONB | 旧标签字段，兼容保留 |
| `highlights` | JSONB | 重点原句数组；最多由 AI 建议 3 条，可人工增删 |
| `ai_classify_status` | TEXT | NULL/pending/done/failed |
| `ai_classified_at` | TIMESTAMPTZ | 分类成功时间 |
| `reviewed_at` | TIMESTAMPTZ | 闸门一:标记已看 |
| `promoted_at` | TIMESTAMPTZ | 闸门二:入脑/落箱时间(knowledge 走两道,fragment 落箱也记此) |
| `deleted_at` | TIMESTAMPTZ | 软删,原文件仍在 |
| `created_at` / `updated_at` | TIMESTAMPTZ | 创建/更新 |

索引:`idx_items_status`、`idx_items_theme`、`idx_items_use`、`idx_items_deleted`。

Vision 仍生成旧 `theme/use_tag/granularity` 供兼容链路使用；统一分类 Worker 写入 `entry_type/domain/main_topic/related_topics/tags`，不覆盖旧字段。截图 `source` 默认写“截图”。

**`ai_output` JSONB 结构**(由 `vision.normalize` 产出,worker 原样存):
```jsonc
{
  "title": "止损的纪律",          // 原文标题,可 null
  "theme": "trading",             // 六类之一,非法值兜底 other
  "use_tag": "方法",              // 五类之一,非法值 null
  "granularity": "knowledge",     // knowledge/fragment/asset
  "summary": "……",
  "is_ocr_suitable": true,
  "ocr_text": "……",              // is_ocr_suitable=false 时 null
  "suggested_theme": "运动",      // 现有分类装不下时的新分类候选,否则 null(分类自动生长的数据源)
  "quality": "干货",              // 干货/反面样本/无信息量(清库的数据源)
  "_raw_content": "模型原始返回"   // 备查
}
// 处理失败时改存:{ "_error": "错误信息", "_attempts": 2 }  ← worker 据此重试到上限
```

**`ai_insight` JSONB 结构**(由 `vision.call_insight` 产出,`/insight` 端点缓存):
```jsonc
{
  "explanation": "把这张图讲明白 + 一句看法",  // 标为「AI 补充」,与原文分开
  "quality": "干货",
  "quality_note": "为什么这么判断",
  "suggested_theme": "运动",                  // 现有分类装不下时提议,否则 null
  "suggested_theme_reason": "……"
}
```

### `image.contents` — 第三层:文字(可多版本)

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `item_id` | BIGINT FK→items ON DELETE CASCADE | 所属条目 |
| `raw_text` | TEXT | Vision/OCR 原文,未清洗 |
| `clean_text` | TEXT | 机械清洗后的成品(见 `clean.py`) |
| `extraction_method` | TEXT | vision/pdftotext/ocr |
| `cleaning_method` | TEXT | rules/ai/rules+ai |
| `language` | TEXT | 语种(暂未填充) |
| `is_current` | BOOLEAN DEFAULT true | 是否当前版本(多版本时取 true 的最新) |
| `created_at` | TIMESTAMPTZ | 创建时间 |

索引:`idx_contents_item`。

---

## 关系图(文字版)

```
image.files ──1:N── image.items ──1:N── image.contents
                        │ (入脑/落箱时)
                        ▼
core.sources(origin=image/files) ──┐
core.sources(origin=core/entries) ─┤
                                    ├─→ core.knowledge ──N:N── core.tags
                                    └─→ core.notes
core.entries ─(归位 file)→ core.sources → core.knowledge / core.notes
```

**向量(pgvector)现不做**:`core.knowledge` 预留 `embedding vector(1536)` 注释,将来 `CREATE EXTENSION vector` + 取消注释即可,同库同备份。Qdrant 对单人自托管是纯负债。
