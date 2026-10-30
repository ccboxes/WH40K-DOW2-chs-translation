from __future__ import annotations

import os
import unittest

from dow2chs.games import _normalize_override


class GamesTests(unittest.TestCase):
    def test_git_bash_drive_path_is_normalized_on_windows(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows only")
        self.assertEqual(_normalize_override("/d/Game/DOW2"), "D:/Game/DOW2")
        self.assertEqual(_normalize_override("D:/Game/DOW2"), "D:/Game/DOW2")


if __name__ == "__main__":
    unittest.main()
