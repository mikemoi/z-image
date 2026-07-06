"""Regression tests for 2026-07-06 review fixes."""
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import HTTPException

from file_storage import ext_from_name, path_from_record, validate_upload_meta
from psycopg.types.json import Jsonb
from routers.admin import _apply_subtopic_migrations
from routers.items import _reading_queue
from routers.settings import classification_schema
from worker import _upsert_candidate


class UploadValidationTests(unittest.TestCase):
    def test_upload_extension_allowlist(self):
        self.assertEqual(ext_from_name("Screen Shot.PNG"), "png")
        with self.assertRaises(HTTPException) as ctx:
            validate_upload_meta(Mock(filename="payload.exe"))
        self.assertEqual(ctx.exception.status_code, 415)


class FilePathDerivationTests(unittest.TestCase):
    def test_checksum_path_prefers_current_files_root_layout(self):
        with patch("file_storage.IMAGE_DIR", Path("/new/root/image")):
            path = path_from_record(
                "abc123",
                db_path="/old/container/image/abc123.png",
                original_filename="ignored.jpg",
            )
        self.assertEqual(path, Path("/new/root/image/abc123.png"))


class CandidateUpsertTests(unittest.TestCase):
    def test_candidate_upsert_is_single_statement(self):
        conn = Mock()
        _upsert_candidate(conn, "tag", "新标签", "身心", "药物", "我", Jsonb([{"id": 1}]))
        sql = conn.execute.call_args.args[0]
        self.assertIn("ON CONFLICT", sql)
        self.assertIn("jsonb_set", sql)


class ClassificationSchemaEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_endpoint_uses_backend_ordered_source(self):
        schema = await classification_schema()
        self.assertEqual(schema.entry_types, ["想法", "知识", "资料", "记录", "规则"])
        self.assertEqual(schema.domains, ["身心", "生活", "能力", "财务", "方向"])
        self.assertEqual(schema.sources, ["我", "图片", "文件"])
        self.assertIn("药物", schema.topics_by_domain["身心"])
        self.assertIn("专注达", schema.sub_topics_by_topic["药物"])


class ItemsQueueTests(unittest.TestCase):
    def test_reading_queue_reports_total_not_page_size(self):
        now = datetime.now(timezone.utc)
        row = {
            "id": 1, "file_id": 2, "checksum": "abc", "status": "ok",
            "title": "t", "summary": "s", "theme": None, "use_tag": None,
            "granularity": None, "entry_type": "知识", "domain": "身心",
            "main_topic": "药物", "sub_topic": "专注达", "related_topics": None,
            "tags": None, "source": "图片", "topics": None, "highlights": None,
            "ai_classify_status": "done", "reviewed_at": None, "promoted_at": None,
            "created_at": now,
        }

        class Result:
            def __init__(self, value):
                self.value = value
            def fetchone(self):
                return {"c": 42}
            def fetchall(self):
                return [row]

        class Conn:
            def execute(self, sql, params=None):
                return Result(sql)

        @contextmanager
        def fake_get_conn():
            yield Conn()

        with patch("routers.items.get_conn", fake_get_conn):
            result = _reading_queue("true", 1, "i.created_at ASC")
        self.assertEqual(result.total, 42)
        self.assertEqual(len(result.items), 1)


class AdminMigrationTests(unittest.TestCase):
    def test_subtopic_migrations_execute_deterministic_updates(self):
        conn = Mock()
        _apply_subtopic_migrations(conn, "core.entries")
        self.assertEqual(conn.execute.call_count, 8)
        sqls = "\n".join(call.args[0] for call in conn.execute.call_args_list)
        self.assertIn("UPDATE core.entries", sqls)
        self.assertIn("related_topics", sqls)
        params = [call.args[1] for call in conn.execute.call_args_list]
        self.assertTrue(any("住家证明" in p for p in params))


if __name__ == "__main__":
    unittest.main()
