"""不访问数据库、不调用 OpenRouter 的分类契约回归测试。"""
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from pydantic import ValidationError

from classify import normalize
from models.entries import EntryCreate, EntryUpdate
from routers.entries import create_entry, reclassify, update_entry


class _FakeResult:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _FakeConnection:
    def __init__(self):
        self.params = None

    def execute(self, _sql, params=None):
        self.params = params
        now = datetime.now(timezone.utc)
        return _FakeResult({
            "id": 1, "kind": params[0], "body": params[1], "status": "filed",
            "mood": params[2], "pinned": params[3], "logged_for": params[4],
            "source_item_id": params[5], "theme": None, "promoted_at": None,
            "entry_type": params[6], "domain": params[7], "use_tag": params[8],
            "source": params[9], "topics": None, "ai_classify_status": "pending",
            "highlights": params[11],
            "ai_classified_at": None, "ai_classify_output": None,
            "created_at": now, "updated_at": now,
        })

    def commit(self):
        pass


class _CaptureConnection:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        now = datetime.now(timezone.utc)
        return _FakeResult({
            "id": 7, "kind": "idea", "body": "人工修改", "status": "filed",
            "mood": None, "pinned": False, "logged_for": None,
            "source_item_id": None, "theme": None, "promoted_at": None,
            "entry_type": "规则", "domain": None, "use_tag": None,
            "source": "自己", "topics": None, "ai_classify_status": "done",
            "highlights": None,
            "ai_classified_at": None, "ai_classify_output": None,
            "created_at": now, "updated_at": now,
        })

    def commit(self):
        pass


class ClassificationContractTests(unittest.TestCase):
    def test_normalize_accepts_fixed_values_and_trims_topics(self):
        out = normalize({
            "entry_type": "想法", "domain": "身心", "use_tag": "参考",
            "topics": [" ADHD ", "药物", "", "他人经验", "一", "二", "三"],
            "highlights": [" 第一句。 ", "第二句。", "第三句。", "第四句。"],
        })
        self.assertEqual(out["entry_type"], "想法")
        self.assertEqual(out["domain"], "身心")
        self.assertEqual(out["use_tag"], "参考")
        self.assertEqual(out["topics"], ["ADHD", "药物", "他人经验", "一", "二"])
        self.assertEqual(out["highlights"], ["第一句。", "第二句。", "第三句。"])

    def test_normalize_rejects_unknown_fixed_values(self):
        out = normalize({"entry_type": "文章", "domain": "工作", "use_tag": "证据"})
        self.assertIsNone(out["entry_type"])
        self.assertIsNone(out["domain"])
        self.assertIsNone(out["use_tag"])

    def test_entry_models_enforce_fixed_enums(self):
        EntryCreate(body="合法", entry_type="句子", domain="方向", use_tag="存档")
        EntryUpdate(entry_type="记录", domain="生活", use_tag="决策")
        with self.assertRaises(ValidationError):
            EntryCreate(body="非法", entry_type="文章")
        with self.assertRaises(ValidationError):
            EntryUpdate(use_tag="证据")

    def test_entry_models_accept_highlights(self):
        payload = EntryCreate(body="先做一步。再看结果。", highlights=["先做一步。"])
        self.assertEqual(payload.highlights, ["先做一步。"])


class EntrySourceRuleTests(unittest.IsolatedAsyncioTestCase):
    async def _create(self, source_item_id):
        conn = _FakeConnection()

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("routers.entries.get_conn", fake_get_conn):
            entry = await create_entry(EntryCreate(body="来源测试", source_item_id=source_item_id))
        return entry

    async def test_without_source_item_is_own(self):
        entry = await self._create(None)
        self.assertEqual(entry.source, "自己")

    async def test_with_source_item_is_screenshot(self):
        entry = await self._create(42)
        self.assertEqual(entry.source, "截图")


class EntryClassificationWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_classification_locks_ai_status(self):
        conn = _CaptureConnection()

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("routers.entries.get_conn", fake_get_conn):
            entry = await update_entry(7, EntryUpdate(entry_type="规则"))
        self.assertEqual(entry.ai_classify_status, "done")
        sql, params = conn.calls[0]
        self.assertIn("ai_classify_status", sql)
        self.assertIn("done", params)

    async def test_reclassify_clears_fields_and_sets_pending(self):
        conn = _CaptureConnection()

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("routers.entries.get_conn", fake_get_conn):
            result = await reclassify(7)
        self.assertTrue(result.ok)
        sql, _params = conn.calls[0]
        self.assertIn("entry_type=NULL", sql)
        self.assertIn("ai_classify_status='pending'", sql)


if __name__ == "__main__":
    unittest.main()
