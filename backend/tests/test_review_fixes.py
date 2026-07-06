"""Regression tests for 2026-07-06 review fixes."""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import HTTPException

from file_storage import ext_from_name, path_from_record, validate_upload_meta
from psycopg.types.json import Jsonb
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


if __name__ == "__main__":
    unittest.main()
