from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dow2chs.ucs import BOM, CRLF, Entry, UcsDocument, UcsError
from dow2chs.ucsjson import document_to_payload, pack_file, payload_to_document, unpack_file


class UcsJsonTests(unittest.TestCase):
    def test_payload_roundtrip(self) -> None:
        document = UcsDocument(
            entries=[Entry("1", "a\tb"), Entry("2", "line\nline")],
            has_bom=True,
            final_newline=True,
        )
        self.assertEqual(payload_to_document(document_to_payload(document)), document)

    def test_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.ucs"
            unpacked = root / "unpacked.json"
            packed = root / "packed.ucs"
            source.write_bytes(
                (BOM + "1\thello\r\n2\tworld\r\n").encode("utf-16-le")
            )
            self.assertEqual(unpack_file(source, unpacked), 2)
            self.assertEqual(pack_file(unpacked, packed), 2)
            self.assertEqual(packed.read_bytes(), source.read_bytes())

    def test_bad_schema(self) -> None:
        with self.assertRaises(UcsError):
            payload_to_document({"schema": "other", "encoding": "utf-16-le", "entries": []})

    def test_unpack_json_is_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.ucs"
            unpacked = root / "unpacked.json"
            source.write_bytes((BOM + "1\t中文\r\n").encode("utf-16-le"))
            unpack_file(source, unpacked)
            data = json.loads(unpacked.read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["text"], "中文")


if __name__ == "__main__":
    unittest.main()
