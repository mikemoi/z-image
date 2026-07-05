"""PostgreSQL 连接池。用 psycopg3 的 connection_pool。"""
from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from config import DATABASE_URL

# 单用户,小池子足够
pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=False)


def open_pool():
    pool.open()


def close_pool():
    pool.close()


@contextmanager
def get_conn():
    """从池取一条连接,行以 dict 形式返回。"""
    with pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn


def ensure_schema():
    """轻量运行时迁移:保证 init.sql 之后新增的列/表存在(已部署的库不会重跑 init.sql)。
    全部 IF NOT EXISTS,幂等安全。"""
    with get_conn() as conn:
        conn.execute("ALTER TABLE image.items ADD COLUMN IF NOT EXISTS ai_insight JSONB")
        # 统一 5 维分类也用到截图(source 隐含=截图;use_tag 沿用 Vision;补 type/domain/topics)
        conn.execute("ALTER TABLE image.items ADD COLUMN IF NOT EXISTS entry_type TEXT")
        conn.execute("ALTER TABLE image.items ADD COLUMN IF NOT EXISTS domain TEXT")
        conn.execute("ALTER TABLE image.items ADD COLUMN IF NOT EXISTS topics JSONB")
        conn.execute("ALTER TABLE image.items ADD COLUMN IF NOT EXISTS ai_classify_status TEXT")
        conn.execute("ALTER TABLE image.items ADD COLUMN IF NOT EXISTS ai_classified_at TIMESTAMPTZ")
        # v0.3 文字入口:手写/剪藏的文字条目(速记/日志/计划/剪藏),复用 core,靠 kind 区分
        conn.execute("""
            CREATE TABLE IF NOT EXISTS core.entries (
                id         BIGSERIAL PRIMARY KEY,
                kind       TEXT NOT NULL,                       -- note|log|plan|clip
                body       TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'inbox',       -- inbox|filed
                mood       TEXT,                                -- 日志可选心情
                pinned     BOOLEAN NOT NULL DEFAULT false,      -- 计划钉住
                logged_for DATE,                                -- 日志:事情发生的日期
                deleted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_kind    ON core.entries (kind)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_status  ON core.entries (status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_logged  ON core.entries (logged_for)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_deleted ON core.entries (deleted_at)")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS source_item_id BIGINT")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS theme TEXT")          # 想法可打主题
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS promoted_at TIMESTAMPTZ")  # 想法已精选入脑
        # 统一分类体系。保留 kind/theme 等旧字段,新字段先用于 entries 并为后续 AI 分类预留状态。
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS entry_type TEXT")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS domain TEXT")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS use_tag TEXT")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS source TEXT")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS topics JSONB")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS ai_classify_status TEXT DEFAULT 'pending'")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS ai_classified_at TIMESTAMPTZ")
        conn.execute("ALTER TABLE core.entries ADD COLUMN IF NOT EXISTS ai_classify_output JSONB")
        # v0.3 设置:通用 kv(现用于 OCR/问问AI 模型切换,以后阈值/主题等也可放这)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS core.settings (
                key        TEXT PRIMARY KEY,
                value      TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
        conn.commit()


def check_db() -> bool:
    """健康检查:能否连通并执行一条查询。"""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
