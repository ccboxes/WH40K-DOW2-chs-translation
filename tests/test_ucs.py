from __future__ import annotations

import unittest

from dow2chs.ucs import BOM, CRLF, Entry, UcsDocument, UcsError, parse_bytes, serialize


class UcsTests(unittest.TestCase):
    def test_roundtrip_preserves_tabs_spaces_and_lone_lf(self) -> None:
        document = UcsDocument(
            entries=[
                Entry("1", "plain"),
                Entry("2", "    •\tReduce armor"),
                Entry("3", "line one\nline two"),
                Entry("4", "trailing   "),
            ]
        )
        data = serialize(document)
        self.assertTrue(data.startswith(BOM.encode("utf-16-le")))
        self.assertTrue(data.endswith(CRLF.encode("utf-16-le")))

        parsed = parse_bytes(data, strict_source=True)
        self.assertEqual(parsed.entries, document.entries)
        self.assertEqual(serialize(parsed), data)

    def test_rejects_missing_bom_and_bad_rows(self) -> None:
        no_bom = "1\ttext\r\n".encode("utf-16-le")
        with self.assertRaises(UcsError):
            parse_bytes(no_bom, strict_source=True)

        with self.assertRaises(UcsError):
            parse_bytes((BOM + "1\ttext\n").encode("utf-16-le"), strict_source=True)

        with self.assertRaises(UcsError):
            parse_bytes((BOM + "not-a-key\ttext\r\n").encode("utf-16-le"))

        with self.assertRaises(UcsError):
            parse_bytes((BOM + "1\tone\r\n1\ttwo\r\n").encode("utf-16-le"))

    def test_final_newline_is_optional_outside_strict_mode(self) -> None:
        data = (BOM + "1\ttext").encode("utf-16-le")
        parsed = parse_bytes(data)
        self.assertFalse(parsed.final_newline)
        self.assertEqual(serialize(parsed), data)


if __name__ == "__main__":
    unittest.main()
