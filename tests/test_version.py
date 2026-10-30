from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dow2chs.version import changelog_has_version, read_version, set_version


class VersionTests(unittest.TestCase):
    def test_set_version_moves_unreleased_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            version_path = root / "VERSION"
            changelog = root / "CHANGELOG.md"
            version_path.write_text("0.0.0\n", encoding="utf-8")
            changelog.write_text(
                "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- 新功能\n\n## [0.0.1]\n\n- 旧版本\n",
                encoding="utf-8",
            )
            set_version("0.1.0", version_path, changelog)
            self.assertEqual(read_version(version_path), "0.1.0")
            text = changelog.read_text(encoding="utf-8")
            self.assertTrue(changelog_has_version("0.1.0", changelog))
            self.assertIn("- 新功能", text.split("## [0.1.0]")[1])
            self.assertNotIn("- 新功能", text.split("## [0.0.1]")[1])

    def test_rejects_bad_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                set_version("1.0", root / "VERSION", root / "CHANGELOG.md")


if __name__ == "__main__":
    unittest.main()
