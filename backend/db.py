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


def check_db() -> bool:
    """健康检查:能否连通并执行一条查询。"""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
