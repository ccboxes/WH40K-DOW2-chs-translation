from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dow2chs.catalog import CatalogError, load_catalog, save_catalog


class CatalogTests(unittest.TestCase):
    def test_roundtrip_unicode_and_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.ndjson"
            data = {"10": "第二行\n下一行", "2": "带\tTAB 的译文", "1": "你好"}
            save_catalog(data, path)
            self.assertEqual(load_catalog(path), data)

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual([line.split('"key":"')[1].split('"')[0] for line in lines], ["1", "2", "10"])

    def test_rejects_empty_translation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.ndjson"
            path.write_text('{"key":"1","text":""}\n', encoding="utf-8")
            with self.assertRaises(CatalogError):
                load_catalog(path)


if __name__ == "__main__":
    unittest.main()
