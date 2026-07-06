"""后台处理:捞 review 且未处理的 item,过 Vision,落库。

- 可续跑:重启后自然接着捞 ai_output IS NULL 的。
- 失败重试:失败写入 _attempts,超过 VISION_MAX_ATTEMPTS 停在 review 等人工。
- 每日预算:超过 VISION_DAILY_BUDGET 当天不再调,次日/重启恢复。
- 任何失败不阻塞下一个。
"""
import asyncio
import logging
from datetime import date

from psycopg.types.json import Jsonb

from db import get_conn
from vision import call_vision
from clean import clean_text
from settings_store import ocr_model
from config import (
    VISION_DAILY_BUDGET, VISION_MAX_ATTEMPTS, WORKER_POLL_SECONDS, CLASSIFY_MAX_ATTEMPTS,
)
from classification_schema import normalize_source
from file_storage import path_from_record

log = logging.getLogger("zbrain.worker")

# ── 每日预算(进程内计数,跨天自动归零) ─────────────────────────────────────
_budget_date = date.today()
_budget_used = 0
_lock = asyncio.Lock()


async def _take_budget() -> bool:
    """占用一次预算;超额返回 False。"""
    global _budget_date, _budget_used
    async with _lock:
        today = date.today()
        if today != _budget_date:
            _budget_date, _budget_used = today, 0
        # 预算 <= 0 视为不限制(仍累加计数,供「我的」显示当日调用数)
        if VISION_DAILY_BUDGET > 0 and _budget_used >= VISION_DAILY_BUDGET:
            return False
        _budget_used += 1
        return True


def pending_count() -> int:
    """还没处理完的候选数(仅内部/调试用,前端只用 working 布尔,不展示此数字)。"""
    try:
        with get_conn() as conn:
            return conn.execute(
                """SELECT count(*) AS c
                   FROM image.items i
                   WHERE i.status = 'review' AND i.deleted_at IS NULL
                     AND (i.ai_output IS NULL
                          OR (i.ai_output ? '_error'
                              AND COALESCE((i.ai_output->>'_attempts')::int, 0) < %s))""",
                (VISION_MAX_ATTEMPTS,),
            ).fetchone()["c"]
    except Exception:
        return 0


def budget_status() -> dict:
    n = pending_count()
    return {
        "date": str(_budget_date),
        "used": _budget_used,
        "limit": VISION_DAILY_BUDGET,
        "unlimited": VISION_DAILY_BUDGET <= 0,
        "pending": n,        # 调试用;UI 不展示数字
        "working": n > 0,    # UI 只用这个:AI 是否在整理
    }


# ── 取候选 ───────────────────────────────────────────────────────────────────
def _fetch_eligible(limit: int) -> list[dict]:
    """status='review' 且(从未处理 或 失败但未超重试上限)。"""
    with get_conn() as conn:
        return conn.execute(
            """SELECT i.id, f.checksum, f.file_path, f.original_filename
               FROM image.items i
               JOIN image.files f ON f.id = i.file_id
               WHERE i.status = 'review'
                 AND i.deleted_at IS NULL
                 AND (
                     i.ai_output IS NULL
                     OR (i.ai_output ? '_error'
                         AND COALESCE((i.ai_output->>'_attempts')::int, 0) < %s)
                 )
               ORDER BY i.created_at ASC
               LIMIT %s""",
            (VISION_MAX_ATTEMPTS, limit),
        ).fetchall()


# ── 处理单个 ─────────────────────────────────────────────────────────────────
async def process_item(item_id: int, file_path: str) -> bool:
    """处理一个 item。成功 True(status→ok),失败 False(留 review + 记 _attempts)。"""
    result = _cached_vision_result(item_id)
    if result is None:
        try:
            result = await call_vision(file_path, model=ocr_model())
        except Exception as e:  # noqa: BLE001 —— 外部调用兜底,不阻塞
            log.warning("vision failed for item %s: %s", item_id, e)
            _record_failure(item_id, str(e))
            return False

    try:
        with get_conn() as conn:
            conn.execute(
                """UPDATE image.items
                   SET status='ok', title=%s, theme=%s, use_tag=%s,
                       granularity=%s, summary=%s, is_ocr_suitable=%s,
                       ai_output=%s, updated_at=now()
                   WHERE id=%s""",
                (result["title"], result["theme"], result["use_tag"],
                 result["granularity"], result["summary"], result["is_ocr_suitable"],
                 Jsonb(result), item_id),
            )
            if result["is_ocr_suitable"] and result["ocr_text"]:
                cleaned = clean_text(result["ocr_text"])
                conn.execute(
                    """INSERT INTO image.contents
                           (item_id, raw_text, clean_text, extraction_method, cleaning_method)
                       VALUES (%s, %s, %s, 'vision', 'rules')""",
                    (item_id, result["ocr_text"], cleaned),
                )
            conn.commit()
        return True
    except Exception as e:  # noqa: BLE001 —— 落库失败也兜底
        log.warning("db write failed for item %s: %s", item_id, e)
        _record_failure(item_id, f"db: {e}", result)
        return False


def _cached_vision_result(item_id: int) -> dict | None:
    try:
        with get_conn() as conn:
            prev = conn.execute(
                "SELECT ai_output FROM image.items WHERE id=%s", (item_id,)
            ).fetchone()
        if prev and isinstance(prev.get("ai_output"), dict):
            cached = prev["ai_output"].get("_vision_result")
            return cached if isinstance(cached, dict) else None
    except Exception as e:  # noqa: BLE001
        log.error("could not read cached vision result for item %s: %s", item_id, e)
    return None


def _record_failure(item_id: int, msg: str, vision_result: dict | None = None):
    """把失败次数累加进 ai_output,status 保持 review。"""
    try:
        with get_conn() as conn:
            prev = conn.execute(
                "SELECT ai_output FROM image.items WHERE id=%s", (item_id,)
            ).fetchone()
            attempts = 0
            if prev and prev["ai_output"] and isinstance(prev["ai_output"], dict):
                attempts = int(prev["ai_output"].get("_attempts", 0))
            payload = {"_error": msg[:500], "_attempts": attempts + 1}
            if vision_result is not None:
                payload["_vision_result"] = vision_result
            conn.execute(
                "UPDATE image.items SET ai_output=%s, updated_at=now() WHERE id=%s",
                (Jsonb(payload), item_id),
            )
            conn.commit()
    except Exception as e:  # noqa: BLE001
        log.error("could not record failure for item %s: %s", item_id, e)


# ── 文字条目自动分类(和 Vision 并行；source 由入口确定) ──────────────
def _fetch_pending_entries(limit: int) -> list[dict]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT id, body, COALESCE(source, '我') AS source FROM core.entries
               WHERE deleted_at IS NULL
                 AND (ai_classify_status IS NULL OR ai_classify_status = 'pending'
                      OR (ai_classify_status = 'failed'
                          AND COALESCE((ai_classify_output->>'_attempts')::int, 0) < %s))
               ORDER BY created_at ASC LIMIT %s""",
            (CLASSIFY_MAX_ATTEMPTS, limit),
        ).fetchall()


def _is_empty_classification(r: dict) -> bool:
    """模型完全没归到类:类型/领域/主题都空,视为失败而不是"完成但空"。"""
    return not (r.get("entry_type") or r.get("domain") or r.get("main_topic"))


async def classify_entry(entry_id: int, body: str, source: str = "我") -> bool:
    """给一条文字打分类。成功 True(status→done),失败 False(记 failed,可续跑到上限)。"""
    from classify import call_classify
    from settings_store import classify_model
    try:
        r = await call_classify(body, model=classify_model())
    except Exception as e:  # noqa: BLE001
        log.warning("classify failed for entry %s: %s", entry_id, e)
        _mark_classify_failed(entry_id, str(e))
        return False
    if _is_empty_classification(r):
        log.warning("classify returned empty result for entry %s", entry_id)
        _mark_classify_failed(entry_id, "empty classification result")
        return False
    try:
        with get_conn() as conn:
            conn.execute(
                """UPDATE core.entries
                   SET entry_type = COALESCE(entry_type, %s),
                       domain     = COALESCE(domain, %s),
                       main_topic = COALESCE(main_topic, %s),
                       sub_topic  = COALESCE(sub_topic, %s),
                       related_topics = COALESCE(related_topics, %s),
                       tags       = COALESCE(tags, %s),
                       ai_classify_status = 'done', ai_classified_at = now(),
                       ai_classify_output = %s, updated_at = now()
                   WHERE id = %s""",
                (r["entry_type"], r["domain"], r["main_topic"], r["sub_topic"],
                 Jsonb(r["related_topics"]) if r["related_topics"] else None,
                 Jsonb(r["tags"]) if r["tags"] else None,
                 Jsonb(r), entry_id),
            )
            _upsert_candidates(conn, r, "entry", entry_id, normalize_source(source, "我") or "我")
            conn.commit()
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("classify db write failed for entry %s: %s", entry_id, e)
        _mark_classify_failed(entry_id, f"db: {e}")
        return False


def _mark_classify_failed(entry_id: int, msg: str):
    """失败次数累加进 ai_classify_output._attempts,达上限前 _fetch_pending_entries 还会捞回来重跑。"""
    try:
        with get_conn() as conn:
            prev = conn.execute(
                "SELECT ai_classify_output FROM core.entries WHERE id=%s", (entry_id,)
            ).fetchone()
            attempts = 0
            if prev and prev["ai_classify_output"] and isinstance(prev["ai_classify_output"], dict):
                attempts = int(prev["ai_classify_output"].get("_attempts", 0))
            conn.execute(
                """UPDATE core.entries SET ai_classify_status = 'failed',
                       ai_classify_output = %s, updated_at = now() WHERE id = %s""",
                (Jsonb({"_error": msg[:500], "_attempts": attempts + 1}), entry_id),
            )
            conn.commit()
    except Exception as e:  # noqa: BLE001
        log.error("could not record classify failure for entry %s: %s", entry_id, e)


def _upsert_candidate(conn, candidate_type: str, name: str, domain: str, main_topic: str,
                      source: str, examples: Jsonb):
    conn.execute(
        """INSERT INTO core.classification_candidates
               (candidate_type, name, domain, main_topic, status, occurrence_count,
                content_count, source_counts, examples)
           VALUES (%s, %s, %s, %s, 'pending', 1, 1, %s, %s)
           ON CONFLICT (candidate_type, name, domain, main_topic) DO UPDATE
           SET occurrence_count = core.classification_candidates.occurrence_count + 1,
               content_count = core.classification_candidates.content_count + 1,
               source_counts = jsonb_set(
                   COALESCE(core.classification_candidates.source_counts, '{}'::jsonb),
                   ARRAY[%s],
                   to_jsonb(
                       COALESCE((core.classification_candidates.source_counts->>%s)::int, 0) + 1
                   ),
                   true
               ),
               examples = COALESCE(core.classification_candidates.examples, '[]'::jsonb)
                          || EXCLUDED.examples,
               updated_at = now()""",
        (
            candidate_type, name, domain, main_topic, Jsonb({source: 1}), examples,
            source, source,
        ),
    )


def _upsert_candidates(conn, result: dict, content_kind: str, content_id: int, source: str):
    examples = Jsonb([{"kind": content_kind, "id": content_id}])
    for name in result.get("candidate_tags") or []:
        _upsert_candidate(conn, "tag", name, result.get("domain") or "", result.get("main_topic") or "", source, examples)
    sub = result.get("candidate_sub_topic")
    if sub:
        _upsert_candidate(
            conn, "sub_topic", sub,
            result.get("candidate_sub_topic_domain") or "",
            result.get("candidate_sub_topic_main_topic") or "",
            source, examples,
        )


# ── 截图也纳入统一分类(读 summary + OCR;旧 theme/use_tag 只兼容保留) ──────
def _fetch_pending_items(limit: int) -> list[dict]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT i.id, i.summary,
                      COALESCE(i.source, '图片') AS source,
                      (SELECT clean_text FROM image.contents c
                       WHERE c.item_id=i.id AND c.is_current=true
                       ORDER BY c.created_at DESC LIMIT 1) AS clean_text
               FROM image.items i
               WHERE i.deleted_at IS NULL AND i.status='ok'
                 AND (i.ai_classify_status IS NULL OR i.ai_classify_status='pending'
                      OR (i.ai_classify_status='failed'
                          AND COALESCE((i.ai_classify_output->>'_attempts')::int, 0) < %s))
                 AND i.summary IS NOT NULL
               ORDER BY i.created_at ASC LIMIT %s""",
            (CLASSIFY_MAX_ATTEMPTS, limit),
        ).fetchall()


async def classify_item(item_id: int, text: str, source: str = "图片") -> bool:
    from classify import call_classify
    from settings_store import classify_model
    try:
        r = await call_classify(text, model=classify_model())
    except Exception as e:  # noqa: BLE001
        log.warning("classify failed for item %s: %s", item_id, e)
        _mark_item_classify_failed(item_id, str(e))
        return False
    if _is_empty_classification(r):
        log.warning("classify returned empty result for item %s", item_id)
        _mark_item_classify_failed(item_id, "empty classification result")
        return False
    try:
        with get_conn() as conn:
            conn.execute(
                """UPDATE image.items
                   SET entry_type = COALESCE(entry_type, %s),
                       domain     = COALESCE(domain, %s),
                       main_topic = COALESCE(main_topic, %s),
                       sub_topic  = COALESCE(sub_topic, %s),
                       related_topics = COALESCE(related_topics, %s),
                       tags       = COALESCE(tags, %s),
                       ai_classify_status='done', ai_classified_at=now(), updated_at=now()
                   WHERE id=%s""",
                (r["entry_type"], r["domain"], r["main_topic"], r["sub_topic"],
                 Jsonb(r["related_topics"]) if r["related_topics"] else None,
                 Jsonb(r["tags"]) if r["tags"] else None,
                 item_id),
            )
            _upsert_candidates(conn, r, "item", item_id, normalize_source(source, "图片") or "图片")
            conn.commit()
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("classify db write failed for item %s: %s", item_id, e)
        _mark_item_classify_failed(item_id, f"db: {e}")
        return False


def _mark_item_classify_failed(item_id: int, msg: str):
    """失败次数累加进 ai_classify_output._attempts,达上限前 _fetch_pending_items 还会捞回来重跑。"""
    try:
        with get_conn() as conn:
            prev = conn.execute(
                "SELECT ai_classify_output FROM image.items WHERE id=%s", (item_id,)
            ).fetchone()
            attempts = 0
            if prev and prev["ai_classify_output"] and isinstance(prev["ai_classify_output"], dict):
                attempts = int(prev["ai_classify_output"].get("_attempts", 0))
            conn.execute(
                """UPDATE image.items SET ai_classify_status='failed',
                       ai_classify_output=%s, updated_at=now() WHERE id=%s""",
                (Jsonb({"_error": msg[:500], "_attempts": attempts + 1}), item_id),
            )
            conn.commit()
    except Exception as e:  # noqa: BLE001
        log.error("could not record classify failure for item %s: %s", item_id, e)


# ── 后台循环 ─────────────────────────────────────────────────────────────────
_task: asyncio.Task | None = None
_classify_task: asyncio.Task | None = None
_stop = asyncio.Event()


async def _classify_loop():
    log.info("classify worker started")
    while not _stop.is_set():
        try:
            entries = _fetch_pending_entries(limit=5)
            items = _fetch_pending_items(limit=5)
            did = False
            for e in entries:
                if not await _take_budget():
                    break
                await classify_entry(e["id"], e["body"], e.get("source") or "我")
                did = True
            for it in items:
                if not await _take_budget():
                    break
                txt = " ".join(filter(None, [it.get("summary"), it.get("clean_text")]))
                await classify_item(it["id"], txt, it.get("source") or "图片")
                did = True
        except Exception as e:  # noqa: BLE001
            log.error("classify cycle error: %s", e)
            did = False
        try:
            await asyncio.wait_for(_stop.wait(), timeout=0.5 if did else WORKER_POLL_SECONDS)
        except asyncio.TimeoutError:
            pass
    log.info("classify worker stopped")


async def _loop():
    log.info("worker started (budget=%s/day, poll=%ss)", VISION_DAILY_BUDGET, WORKER_POLL_SECONDS)
    while not _stop.is_set():
        try:
            items = _fetch_eligible(limit=5)
            did_work = False
            for it in items:
                if not await _take_budget():
                    log.info("daily budget exhausted (%s), pausing", VISION_DAILY_BUDGET)
                    break
                file_path = path_from_record(it["checksum"], it["file_path"], it["original_filename"])
                await process_item(it["id"], str(file_path))
                did_work = True
        except Exception as e:  # noqa: BLE001 —— 循环自身不能挂
            log.error("worker cycle error: %s", e)
            did_work = False
        # 有活干就短歇继续,空闲则按轮询间隔等
        try:
            await asyncio.wait_for(_stop.wait(), timeout=0.5 if did_work else WORKER_POLL_SECONDS)
        except asyncio.TimeoutError:
            pass
    log.info("worker stopped")


def start_worker():
    global _task, _classify_task
    _stop.clear()
    _task = asyncio.create_task(_loop())
    _classify_task = asyncio.create_task(_classify_loop())


async def stop_worker():
    _stop.set()
    for t in (_task, _classify_task):
        if t:
            await t
