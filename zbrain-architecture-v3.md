# zbrain · 第二脑 · v3 终稿(直接开项目蓝图)

> 综合存储库 = 你的第二脑。所有碎片和想存的东西数字化,方便你用。
> 基于 40 张真实截图样本校准。z-image 是第一个入口,聚焦图片。

---

## 0. 本质与准绳(最高优先级,先读)

**这是什么:** 一个自托管、单用户的综合存储库,即第二脑。你所有的碎片、截图、笔记、想存的东西都数字化进来,方便你在需要时用。

**唯一准绳:** "方便我用" 压倒 "存得全"。凡是增加"存的负担"但不增加"用的便利"的功能一律砍。你只关心三件事:
- **进(数字化):** 存进去毫不费力 —— 尤其截图,上传即走,手机当场清空
- **用(方便用):** 需要时找得到 / 撞得见 —— 四种遇见
- **删(提纯):** 看到"什么玩意"能一键删掉 —— 库越用越干净,不变成新焦虑源

**三条气质(贯穿所有设计):**
- anti-anxiety:无 streak、无待办计数、无焦虑指标。删除无劝阻无愧疚。
- self-use:成功标准是"我真的天天用它、手机真的清空了",不是完备度。
- 别变成整理花园:不逼用户手动经营结构。自动流水线优先,手动整理留给用户主动发起。

**z-image 是第一个入口**(手机图 5-6000 张,最痛、增量每天约 50)。PDF / 笔记 / 剪藏是后续入口,复用 core 层。

---

## 1. 真实数据教训(40 张样本得出,务必内化)

- 图片约 90% 是"文字截图"而非照片 → is_ocr_suitable 多为 true。省钱靠两段式(先判适不适合,只对适合的花第二次 OCR),不靠跳过。
- 一大半内容与交易相关,但**用户还在做交易,要沉淀方法论 + 观察群体避坑**(看别人栽哪、我规避),不是找共鸣。交易不设隔离类,靠 theme=trading + use 维度区分。
- "情绪帖"对用户是**反面教材/群体样本**("十年没头绪""3次爆仓"),有提炼价值,use=避坑,该进脑。只有纯无信息量的("写得真好"评论流)才 archive/useless。
- 价值在图不在字的多(K线/形态/手绘/白板拍照)→ OCR 无意义,存原图 + Vision 一句话 summary,summary 是唯一检索抓手。
- 噪音多种:状态栏、平台UI(点赞/关注/搜索框)、背景图穿透(正文浮在照片上)、相册胶卷、无信息量评论流。后几种机械规则搞不定,交给 Vision。
- 长文常被拆成多张连续截图 → 初版各自独立存,承认残缺,不强行拼接(第二刀)。
- 繁体/中英/中俄混排存在 → 必须走 Vision,传统 OCR 不行。
- 部分图有**原文标题/问题**(如知乎"一个人最根本的能力是什么?")→ 抓为 title,信息量比 AI summary 还高。

---

## 2. 用户工作流:清空 vs 消化,两个节奏分离

**清空节奏(每天,高频,必须零摩擦):** 用户先在手机里初筛(垃圾已删),选约 50 张 → 上传即走 → 立刻从手机相册删掉 → 手机清空,目的当场达成。用户不等 AI。

**消化节奏(随时,低频,无压力):** 后台 AI 慢慢处理完,用户有空时进来看归好的类、review、入脑。没有时间压力,不显示"你有 N 张待处理"。

**两者严格分离:** 上传的反馈是"✓ 已接收 50 张,手机可清空",不是"50 张待处理"。绝不让"没处理完"变成待办焦虑。

**原文是唯一副本的警示:** 用户删手机原图后,zbrain 磁盘的 checksum 原图是唯一副本。→ 原文事实源地位极高,建议给 `/data/zbrain/files` 配定期备份(初版非必须,但需明确告知用户:磁盘挂=图没了)。

---

## 3. 整体架构

```
zbrain(一个 database)
├── core       脑本体(核心资产,跨入口):
│              core.knowledge(精选脑) / core.notes(感悟收集箱)
│              core.sources / core.tags / core.knowledge_tags
├── image      z-image 入口:image.files / image.items / image.contents
└── (spanish / body / 笔记 / 剪藏 等入口以后加,复用 core)

磁盘原文:/data/zbrain/files/image/<checksum>.<ext>
```

**三层存储门槛递减:**
1. `core.knowledge` — 精选脑。成体系、有信息量的知识块。两道闸门、全文检索、将来接 pgvector。
2. `core.notes` — 感悟收集箱。万金油碎片(如"放低期待"),一句一条,低门槛,靠"重新遇见"激活,不混进核心脑(避免稀释)。
3. `image.*` — 原始入口。截图原文事实源 + 加工台。

**数据流:**
```
image.contents.clean_text
  │ granularity 判定
  ├─ knowledge → ①reviewed → ②promote(手动入脑) → core.knowledge(切块+打tag)
  └─ fragment  → ①reviewed(确认是碎片) → core.notes(轻路径,无第二道闸门)
```

---

## 4. 完整 Schema

### 命名约定
全小写下划线;主键 `id`;外键 `<单数表>_id`;时间戳 `_at`;布尔 `is_`;三层文字固定 `raw_text`/`clean_text`;库内不带 z 品牌(schema 即命名空间)。

### core —— 脑本体

```sql
CREATE SCHEMA core;

CREATE TABLE core.sources (
    id            BIGSERIAL PRIMARY KEY,
    origin_schema TEXT NOT NULL,        -- 'image'
    origin_table  TEXT NOT NULL,        -- 'files'
    origin_id     BIGINT NOT NULL,      -- → image.files.id
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 精选脑:成体系知识块
CREATE TABLE core.knowledge (
    id         BIGSERIAL PRIMARY KEY,
    source_id  BIGINT REFERENCES core.sources(id),
    title      TEXT,                    -- 原文标题/问题(如"一个人最根本的能力是什么"),可空
    body       TEXT NOT NULL,           -- 知识块正文(从 clean_text 切出)
    seq        INT,
    summary    TEXT,
    deleted_at TIMESTAMPTZ,             -- 软删
    -- embedding vector(1536)           -- 语义检索时启用 pgvector,现在预留不建
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE core.knowledge ADD COLUMN body_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'')||' '||coalesce(body,''))) STORED;
CREATE INDEX idx_knowledge_tsv ON core.knowledge USING GIN (body_tsv);
CREATE INDEX idx_knowledge_deleted ON core.knowledge (deleted_at);

-- 感悟收集箱:万金油碎片
CREATE TABLE core.notes (
    id           BIGSERIAL PRIMARY KEY,
    source_id    BIGINT REFERENCES core.sources(id),  -- 来自哪张图,可空(手敲的没有)
    body         TEXT NOT NULL,         -- "放低期待,期望低一点,对结果接受度越高"
    use_tag      TEXT,                  -- 心态/避坑/灵感(碎片主要这几种)
    last_seen_at TIMESTAMPTZ,           -- 上次"重新遇见"推送时间,支持轮换
    deleted_at   TIMESTAMPTZ,           -- 软删
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notes_lastseen ON core.notes (last_seen_at);
CREATE INDEX idx_notes_deleted  ON core.notes (deleted_at);

-- 双维度 + 自由细分标签
CREATE TABLE core.tags (
    id   BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,                 -- 'theme'(主题) | 'use'(用途) | 'topic'(自由细分,如"正向反馈")
    UNIQUE (name, kind)
);
INSERT INTO core.tags (name, kind) VALUES
('trading','theme'),('ai','theme'),('adhd','theme'),
('language','theme'),('life','theme'),('other','theme'),
('方法','use'),('避坑','use'),('心态','use'),('工具','use'),('灵感','use');
-- topic 类标签由 AI 建议 + 用户增改,动态生长(如"正向反馈""复利""止损")

CREATE TABLE core.knowledge_tags (
    knowledge_id BIGINT NOT NULL REFERENCES core.knowledge(id) ON DELETE CASCADE,
    tag_id       BIGINT NOT NULL REFERENCES core.tags(id) ON DELETE CASCADE,
    PRIMARY KEY (knowledge_id, tag_id)
);
```

**向量:现在不做,不装 Qdrant。** 将来 `CREATE EXTENSION vector` + 取消 embedding 注释即可,同库同备份天然一致。Qdrant 对单人自托管是纯负债。

### image —— z-image 入口

```sql
CREATE SCHEMA image;

-- 第一层:不可变事实源,只增不改(用户删手机后是唯一副本)
CREATE TABLE image.files (
    id                BIGSERIAL PRIMARY KEY,
    file_path         TEXT NOT NULL,          -- /data/zbrain/files/image/<checksum>.<ext>
    file_type         TEXT NOT NULL,          -- 'image' | 'pdf'
    original_filename TEXT NOT NULL,
    checksum          TEXT NOT NULL,          -- sha256,去重底子
    file_size         BIGINT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_files_checksum ON image.files (checksum);

-- 条目:处理状态 + 双维度 + 粒度 + 标题 + 两道闸门 + 软删
CREATE TABLE image.items (
    id              BIGSERIAL PRIMARY KEY,
    file_id         BIGINT NOT NULL REFERENCES image.files(id),
    status          TEXT NOT NULL DEFAULT 'review', -- 'ok'|'review'|'archive'|'useless'
    title           TEXT,                           -- 原文标题/问题,可空
    summary         TEXT,                           -- 唯一检索抓手(图解/交易/反面教材类)
    theme           TEXT,                           -- 主题
    use_tag         TEXT,                           -- 用途
    granularity     TEXT,                           -- 'knowledge' | 'fragment'
    is_ocr_suitable BOOLEAN DEFAULT false,
    ai_output       JSONB,                          -- AI 完整结构化输出
    reviewed_at     TIMESTAMPTZ,                    -- 闸门一
    promoted_at     TIMESTAMPTZ,                    -- 闸门二(仅 knowledge 走)
    deleted_at      TIMESTAMPTZ,                    -- 软删,原文件仍在
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_items_status   ON image.items (status);
CREATE INDEX idx_items_theme    ON image.items (theme);
CREATE INDEX idx_items_use      ON image.items (use_tag);
CREATE INDEX idx_items_deleted  ON image.items (deleted_at);

-- 第二、三层文字,可多版本
CREATE TABLE image.contents (
    id                BIGSERIAL PRIMARY KEY,
    item_id           BIGINT NOT NULL REFERENCES image.items(id) ON DELETE CASCADE,
    raw_text          TEXT,                   -- Vision/OCR 原文,未清洗
    clean_text        TEXT,                   -- 去噪成品
    extraction_method TEXT,                   -- 'vision'|'pdftotext'|'ocr'
    cleaning_method   TEXT,                   -- 'rules'|'ai'|'rules+ai'
    language          TEXT,
    is_current        BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_contents_item ON image.contents (item_id);
```

**status 只管处理路径,"这是什么"由 theme+use+granularity 回答。** ok/review/archive/useless。

---

## 5. z-image 图片管线

```
POST /api/items/upload (image[])   —— 支持批量
=== 同步(立即返回,手机可清空)===
1. 逐张:存原图 /data/zbrain/files/image/<checksum>.<ext>,算 sha256
2. INSERT image.files(file_type='image')
3. INSERT image.items(file_id, status='review')
4. 立即返回 "已接收 N 张"  ← 用户去删手机原图,不等 AI

=== 后台任务(慢跑,可续跑/重试/限每日预算)===
5. 一次 Vision 调用,返回 JSON:
   { title, theme, use, granularity, summary, is_ocr_suitable, ocr_text? }
6. 分流:
   - is_ocr_suitable=true  → ocr_text=raw_text → 机械清洗 → clean_text
   - is_ocr_suitable=false → 只有 summary(图解/K线/手绘/纯碎片)
7. UPDATE image.items(status='ok', title, theme, use_tag, granularity, summary, is_ocr_suitable, ai_output)
   有文字则 INSERT image.contents(...)
8. 任何失败 → status 保持 'review',不阻塞,人工兜底

=== 消化(用户随时)===
- knowledge 类:review(闸门一) → promote(闸门二,手动) → 切块入 core.knowledge + 打 theme/use/topic tag
- fragment  类:review 确认是碎片 → 直接落 core.notes(无第二道闸门)
```

---

## 6. Vision Prompt(强制 JSON,Claude Code 直接用)

```
你是一个个人第二脑的图片分析器。用户给你一张手机截图或图片。
只返回一个 JSON 对象,不要任何解释、不要 markdown 包裹。

1. title:如果图中有明确的原文标题/问题/主标(如知乎问题、文章标题),原样提取;没有则空字符串。
2. theme(主题,择一):trading / ai / adhd / language / life / other
3. use(用途,用户最可能拿它做什么,择一):
   方法(讲怎么做的体系知识/步骤/系统)、
   避坑(别人踩的坑/失败/爆仓/普遍误区,用户借以反思规避)、
   心态(该保持的状态/情绪调节/认知态度)、
   工具(具体软件/项目/资源)、灵感(触发思考的点子/观点)
4. granularity(粒度,择一):
   knowledge —— 成体系、有信息量、能独立成立的知识(方法/论证/清单/架构)
   fragment  —— 一句孤立的感悟/金句/万金油提醒(去掉它只损失"一句提醒")
5. summary:一句话说清"这张图讲了什么"。
   对图解/K线/形态/手绘/白板等无正文的图,描述其表达的方法或结构
   (例:"葛兰威尔均线八大买卖点示意图"),这是唯一检索抓手。
   fragment 类,summary 可等于那句话本身。
6. is_ocr_suitable:图片主体是否为「值得入库的正文文字」。
   true:文章/回答/笔记/评论正文。
   false:K线图/形态图/手绘/白板拍照/表情包/纯图/无信息量评论流("写得真好")/纯一句金句。
7. 若 is_ocr_suitable=true,提取 ocr_text:
   只提主体正文。必须忽略:顶部状态栏(时间/电量/信号)、平台UI(用户名/头像/时间地点/
   点赞收藏评论转发数/关注按钮/搜索框/下载广告)、背景照片上文字、相册底部缩略图条、
   无信息量礼貌性评论。保留正文原文,不改写。
   若 false,ocr_text 省略或空。

输出:{"title":"","theme":"life","use":"心态","granularity":"fragment","summary":"...","is_ocr_suitable":false}

边界:
- 交易内容:主体在讲"怎么做/为什么/别人栽哪"就归对应 use;拿不准偏"方法",最终入脑用户手动把关。
- 纯情绪宣泄或纯无信息量评论:theme 照填,is_ocr_suitable=false。
- granularity 拿不准时偏 fragment(碎片进 notes 无闸门,更轻;误判损失小)。
```

---

## 7. 四种遇见(用得顺,才是第二脑)

**遇见二·按维度浏览【初版核心】:** 主题 tab × 用途 tab 交叉筛选。按 `use=避坑` 跨所有主题横向拉出所有反面教材;按 `use=心态` 拉出所有心态提醒;按 topic 标签(正向反馈/复利)拉出同簇。这是"整理自己"的主入口。

**遇见三·重新遇见【初版建议做】:** 首页偶尔翻出 3-5 条 last_seen_at 最久的 core.notes 碎片(+老 knowledge),配原图缩略。用户没找它、它来找你——碎片的唯一救赎。看完更新 last_seen_at 轮换。无待办、纯偶遇,符合 anti-anxiety。

**遇见一·搜索【基础设施】:** PG 全文检索(title+body 已建 tsvector),精确找东西时用。零额外成本。

**遇见四·关联【第二刀】:** 看 A 带出相关 B,靠 tag 关联或将来 pgvector 语义相似。

**首页形态:** 上半"重新遇见"推送卡片 + 下半维度入口大按钮(避坑/心态/方法/工具/灵感 + trading/ai/adhd/life)+ 顶部搜索框。

---

## 8. 删除体系(贯穿每层每界面)

**三档,日常只碰第一档,删除无劝阻无愧疚:**
- **删除(一键,爽快):** 任何界面看到"什么玩意",点删除立即从所有列表消失(软删 deleted_at)。手感彻底,眼不见为净。原文件与记录仍在。**日常唯一常用。**
- **回收站(后悔药):** 软删的东西进回收站可找回。不管它就永远躺着。防手滑(尤其原图已是唯一副本)。
- **彻底销毁(清空回收站):** 永久抹磁盘原文件 + 删记录,二次确认,不可恢复。低频。

**删除粒度:**
- 删 item:图 + 其提炼(knowledge/notes)一起消失
- 删 knowledge/notes 单条:图留着,只删这条提炼
- 删"重新遇见"卡片:当场划掉,以后不再遇见

删除按钮出现在:条目列表、详情页、维度浏览页、**重新遇见推送卡片**。所有列表默认 `WHERE deleted_at IS NULL`。

---

## 9. API(初版)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/items/upload` | 批量上传,同步落库立即返回 |
| GET | `/api/items?theme=&use=&status=&granularity=&promoted=&deleted=false` | 列表筛选 |
| GET | `/api/items/{id}` | 详情:原图 + title/theme/use + summary + clean_text |
| PATCH | `/api/items/{id}` | 改 title/theme/use/status/granularity |
| PATCH | `/api/items/{id}/review` | 闸门一 |
| PATCH | `/api/items/{id}/promote` | 闸门二:knowledge 切块入 core |
| POST | `/api/items/{id}/to-note` | fragment 落 core.notes(轻路径) |
| PATCH | `/api/items/{id}/soft-delete` | 软删入回收站 |
| POST | `/api/items/{id}/restore` | 从回收站恢复 |
| DELETE | `/api/items/{id}/purge` | 彻底销毁,二次确认 |
| GET | `/api/feed/resurface` | 重新遇见:取 last_seen_at 最久的 notes |
| GET | `/api/search?q=` | 全文检索 core.knowledge |

鉴权:单用户,header token / basic auth。upload/delete 不裸奔公网。

---

## 10. 前端页面(初版)

1. **上传页** — 批量、进度、反馈"✓ 已接收 N 张,手机可清空"(不显示"待处理")
2. **首页** — 上:重新遇见卡片(可当场删/入脑);下:维度入口(用途×主题按钮)
3. **浏览页** — 双维度 + topic 筛选,每维度数量(不显示"未处理总数")
4. **条目列表** — 卡片:缩略图、title、theme/use 标签、summary、是否 reviewed/入脑、删除
5. **详情页** — 原图(可放大)+ title + theme/use + summary + clean_text + 按钮(改标签/review/入脑或落note/软删/彻底销毁二次确认)
6. **回收站** — 软删项,可恢复 / 彻底销毁

review 界面按用户主要 review 设备优化(待用户确认手机/桌面)。

---

## 11. 批量存量(5-6000 张)

- 可续跑后台队列:限速、限每日预算、失败重试、显示进度。
- **先接新增,别一上来灌存量**:先让工具对"每天约 50 张"有用,养成天天用;存量作为独立"清库任务"分批慢跑,不是 MVP 门槛,否则淹没在待 review 里、违背 anti-anxiety。
- 校准:先拿 30-50 张真实图跑通,核对 title/theme/use/granularity 准不准、summary 有没有用、噪音剥离干不干净,满意再批量。

---

## 12. 技术栈 & 明确不做 & 第二刀

**技术栈:** FastAPI + PostgreSQL(已运行,直接用 zbrain 库)+ React/Vite/PWA(可与后端合并部署);Vision 用 OpenRouter 的 gpt-4.1-mini 或 gemini-flash;Docker + 1Panel + Nginx。建议给 /data/zbrain/files 配定期备份(原图可能是唯一副本)。

**初版不做:** PDF 管线、传统 OCR(tesseract)、自动去重逻辑(仅存 checksum)、向量/pgvector/Qdrant、RAG 问答、长文多图拼接、主题容器(core.topics)、卡片生成、每日推送、多用户、精细切块策略。

**第二刀:** PDF 管线(pdftotext 抽取,后半段复用)、长文连续截图拼接、**主题容器**(core.topics,从高频 topic 标签自然长出,把相关图/碎片/知识归进有名字的容器)、pgvector 语义检索、关联遇见、language/life 等新入口、z-spanish 从 core 取料。
```
