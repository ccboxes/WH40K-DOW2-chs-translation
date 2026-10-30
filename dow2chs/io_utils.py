"""文本文件写出辅助。

``Path.write_text(newline=...)`` 在 Python 3.9 还没有 newline 参数，
这里统一用显式 open，保证 Windows 上也能确定换行符。
"""

from __future__ import annotations

from pathlib import Path


def write_text_exact(path: Path, text: str, *, newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline=newline) as file:
        file.write(text)
