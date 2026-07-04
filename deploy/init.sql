-- zbrain 建表脚本(来自 zbrain-architecture-v3.md §4)
-- 用法:
--   外部 PG:  psql -U postgres -d zbrain -f db/init.sql
--   compose:  自动挂到 /docker-entrypoint-initdb.d/ 首次启动执行
-- 幂等:全部 IF NOT EXISTS / ON CONFLICT,重复执行安全。

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS image;

-- ── core:脑本体 ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS core.sources (
    id            BIGSERIAL PRIMARY KEY,
    origin_schema TEXT NOT NULL,
    origin_table  TEXT NOT NULL,
    origin_id     BIGINT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.knowledge (
    id         BIGSERIAL PRIMARY KEY,
    source_id  BIGINT REFERENCES core.sources(id),
    title      TEXT,
    body       TEXT NOT NULL,
    seq        INT,
    summary    TEXT,
    deleted_at TIMESTAMPTZ,
    body_tsv   tsvector GENERATED ALWAYS AS
        (to_tsvector('simple', coalesce(title,'')||' '||coalesce(body,''))) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_knowledge_tsv     ON core.knowledge USING GIN (body_tsv);
CREATE INDEX IF NOT EXISTS idx_knowledge_deleted ON core.knowledge (deleted_at);

CREATE TABLE IF NOT EXISTS core.notes (
    id           BIGSERIAL PRIMARY KEY,
    source_id    BIGINT REFERENCES core.sources(id),
    body         TEXT NOT NULL,
    use_tag      TEXT,
    last_seen_at TIMESTAMPTZ,
    deleted_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notes_lastseen ON core.notes (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_notes_deleted  ON core.notes (deleted_at);

CREATE TABLE IF NOT EXISTS core.tags (
    id   BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    UNIQUE (name, kind)
);
INSERT INTO core.tags (name, kind) VALUES
('trading','theme'),('ai','theme'),('adhd','theme'),
('language','theme'),('life','theme'),('other','theme'),
('方法','use'),('避坑','use'),('心态','use'),('工具','use'),('灵感','use')
ON CONFLICT (name, kind) DO NOTHING;

CREATE TABLE IF NOT EXISTS core.knowledge_tags (
    knowledge_id BIGINT NOT NULL REFERENCES core.knowledge(id) ON DELETE CASCADE,
    tag_id       BIGINT NOT NULL REFERENCES core.tags(id)      ON DELETE CASCADE,
    PRIMARY KEY (knowledge_id, tag_id)
);

-- v0.3 文字入口:手写/剪藏的文字条目(速记/日志/计划/剪藏),复用 core,靠 kind 区分
CREATE TABLE IF NOT EXISTS core.entries (
    id         BIGSERIAL PRIMARY KEY,
    kind       TEXT NOT NULL,                       -- note|log|plan|clip
    body       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'inbox',       -- inbox|filed
    mood       TEXT,                                -- 日志可选心情
    pinned     BOOLEAN NOT NULL DEFAULT false,      -- 计划钉住
    logged_for DATE,                                -- 日志:事情发生的日期
    source_item_id BIGINT,                          -- 想法来自哪张截图(可空)
    theme      TEXT,                                -- 想法可打主题
    promoted_at TIMESTAMPTZ,                        -- 想法已精选入脑
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_entries_kind    ON core.entries (kind);
CREATE INDEX IF NOT EXISTS idx_entries_status  ON core.entries (status);
CREATE INDEX IF NOT EXISTS idx_entries_logged  ON core.entries (logged_for);
CREATE INDEX IF NOT EXISTS idx_entries_deleted ON core.entries (deleted_at);

-- v0.3 通用设置(kv):现用于 OCR / 问问AI 模型切换
CREATE TABLE IF NOT EXISTS core.settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── image:z-image 入口 ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS image.files (
    id                BIGSERIAL PRIMARY KEY,
    file_path         TEXT NOT NULL,
    file_type         TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    checksum          TEXT NOT NULL,
    file_size         BIGINT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_files_checksum ON image.files (checksum);

CREATE TABLE IF NOT EXISTS image.items (
    id              BIGSERIAL PRIMARY KEY,
    file_id         BIGINT NOT NULL REFERENCES image.files(id),
    status          TEXT NOT NULL DEFAULT 'review',
    title           TEXT,
    summary         TEXT,
    theme           TEXT,
    use_tag         TEXT,
    granularity     TEXT,
    is_ocr_suitable BOOLEAN DEFAULT false,
    ai_output       JSONB,
    ai_insight      JSONB,                  -- v0.3「问问 AI」按需生成的看法(缓存,AI 补充非原文)
    reviewed_at     TIMESTAMPTZ,
    promoted_at     TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_items_status  ON image.items (status);
CREATE INDEX IF NOT EXISTS idx_items_theme   ON image.items (theme);
CREATE INDEX IF NOT EXISTS idx_items_use     ON image.items (use_tag);
CREATE INDEX IF NOT EXISTS idx_items_deleted ON image.items (deleted_at);

CREATE TABLE IF NOT EXISTS image.contents (
    id                BIGSERIAL PRIMARY KEY,
    item_id           BIGINT NOT NULL REFERENCES image.items(id) ON DELETE CASCADE,
    raw_text          TEXT,
    clean_text        TEXT,
    extraction_method TEXT,
    cleaning_method   TEXT,
    language          TEXT,
    is_current        BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_contents_item ON image.contents (item_id);
