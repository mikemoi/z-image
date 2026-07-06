"""不访问数据库、不调用 OpenRouter 的分类契约回归测试。"""
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from pydantic import ValidationError

from classify import normalize
from classification_schema import SUB_TOPICS_BY_TOPIC
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
            "entry_type": params[6], "domain": params[7], "main_topic": params[8],
            "sub_topic": params[9], "related_topics": None, "tags": None, "use_tag": params[12],
            "source": params[13], "topics": None, "ai_classify_status": "pending",
            "highlights": params[15],
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
            "main_topic": None, "sub_topic": None, "related_topics": None, "tags": None,
            "source": "我", "topics": None, "ai_classify_status": "done",
            "highlights": None,
            "ai_classified_at": None, "ai_classify_output": None,
            "created_at": now, "updated_at": now,
        })

    def commit(self):
        pass


class ClassificationContractTests(unittest.TestCase):
    def test_normalize_accepts_fixed_topics_and_limits_tags(self):
        out = normalize({
            "entry_type": "知识", "domain": "身心", "main_topic": "药物",
            "sub_topic": "专注达",
            "related_topics": ["ADHD", "睡眠", "交易"],
            "tags": [" 专注达 ", "反跳", "", "他人经验", "一", "二", "三"],
            "candidate_tags": ["新标签"],
        })
        self.assertEqual(out["entry_type"], "知识")
        self.assertEqual(out["domain"], "身心")
        self.assertEqual(out["main_topic"], "药物")
        self.assertEqual(out["sub_topic"], "专注达")
        self.assertEqual(out["related_topics"], ["ADHD", "睡眠"])
        self.assertEqual(out["tags"], ["专注达", "反跳", "他人经验", "一", "二"])
        self.assertEqual(out["candidate_tags"], ["新标签"])

    def test_normalize_rejects_unknown_fixed_values(self):
        out = normalize({"entry_type": "文章", "domain": "工作", "main_topic": "经济"})
        self.assertIsNone(out["entry_type"])
        self.assertIsNone(out["domain"])
        self.assertIsNone(out["main_topic"])

    def test_entry_models_enforce_fixed_enums(self):
        EntryCreate(body="合法", entry_type="想法", domain="方向", main_topic="规则", sub_topic="不做清单")
        EntryUpdate(entry_type="记录", domain="生活", main_topic="日常")
        with self.assertRaises(ValidationError):
            EntryCreate(body="非法", entry_type="文章")
        with self.assertRaises(ValidationError):
            EntryUpdate(main_topic="经济")
        with self.assertRaises(ValidationError):
            EntryCreate(body="领域不匹配", domain="身心", main_topic="交易")

    def test_related_topics_and_tags_have_limits(self):
        with self.assertRaises(ValidationError):
            EntryCreate(body="过多关联", related_topics=["ADHD", "睡眠", "情绪"])
        with self.assertRaises(ValidationError):
            EntryCreate(body="过多标签", tags=["一", "二", "三", "四", "五", "六"])

    def test_entry_models_accept_highlights(self):
        payload = EntryCreate(body="先做一步。再看结果。", highlights=["先做一步。"])
        self.assertEqual(payload.highlights, ["先做一步。"])

    def test_fixed_subtopics_are_cleaned_and_extended(self):
        self.assertIn("反馈机制", SUB_TOPICS_BY_TOPIC["ADHD"])
        self.assertIn("认知 CBT", SUB_TOPICS_BY_TOPIC["ADHD"])
        self.assertIn("学习方法", SUB_TOPICS_BY_TOPIC["学习"])
        self.assertIn("扛单", SUB_TOPICS_BY_TOPIC["交易"])
        self.assertIn("落子无悔", SUB_TOPICS_BY_TOPIC["决策"])
        self.assertNotIn("住家证明", SUB_TOPICS_BY_TOPIC["居住"])
        self.assertIn("住家证明", SUB_TOPICS_BY_TOPIC["证件"])
        self.assertNotIn("Docker", SUB_TOPICS_BY_TOPIC["编程"])
        self.assertIn("Docker", SUB_TOPICS_BY_TOPIC["服务器"])
        self.assertNotIn("分类系统", SUB_TOPICS_BY_TOPIC["产品"])
        self.assertIn("内容坐标", SUB_TOPICS_BY_TOPIC["产品"])
        self.assertIn("债务风险", SUB_TOPICS_BY_TOPIC["债务"])
        self.assertIn("投资风险", SUB_TOPICS_BY_TOPIC["投资"])
        self.assertNotIn("风险", SUB_TOPICS_BY_TOPIC["债务"])
        self.assertNotIn("风险", SUB_TOPICS_BY_TOPIC["投资"])


class EntrySourceRuleTests(unittest.IsolatedAsyncioTestCase):
    async def _create(self, source_item_id):
        conn = _FakeConnection()

        @contextmanager
        def fake_get_conn():
            yield conn

        with patch("routers.entries.get_conn", fake_get_conn):
            entry = await create_entry(EntryCreate(body="来源测试", source_item_id=source_item_id))
        return entry

    async def test_without_source_item_is_mine(self):
        entry = await self._create(None)
        self.assertEqual(entry.source, "我")

    async def test_with_source_item_still_mine(self):
        entry = await self._create(42)
        self.assertEqual(entry.source, "我")


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
        self.assertIn("main_topic=NULL", sql)
        self.assertIn("sub_topic=NULL", sql)
        self.assertIn("ai_classify_status='pending'", sql)


if __name__ == "__main__":
    unittest.main()
