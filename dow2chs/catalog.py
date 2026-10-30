"""译本目录：每行一个 JSON 对象，按数字 key 排序。

用 NDJSON 而不是一个大 JSON 对象，是为了让 git diff 每次只显示改动的条目，
并且能无损保存 TAB、换行和尾随空格。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .paths import CATALOG_PATH


class CatalogError(ValueError):
    """译本目录格式不合法。"""


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, str]:
    translations: dict[str, str] = {}
    if not path.exists():
        return translations

    with path.open("r", encoding="utf-8", newline="") as file:
        for number, line in enumerate(file, start=1):
            line = line.rstrip("\n")
            if line == "":
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise CatalogError(f"{path}:{number} 不是合法 JSON：{error.msg}") from error
            if not isinstance(record, dict):
                raise CatalogError(f"{path}:{number} 不是 JSON 对象")
            key = record.get("key")
            text = record.get("text")
            if not isinstance(key, str) or not key.isdigit():
                raise CatalogError(f"{path}:{number} 的 key 不是数字字符串")
            if not isinstance(text, str):
                raise CatalogError(f"{path}:{number} 的 text 不是字符串")
            if text == "":
                raise CatalogError(f"{path}:{number}（key {key}）译文为空")
            if "\r" in text:
                raise CatalogError(f"{path}:{number}（key {key}）译文含 CR")
            if key in translations:
                raise CatalogError(f"{path}:{number} 的 key 重复：{key}")
            translations[key] = text

    return translations


def save_catalog(translations: dict[str, str], path: Path = CATALOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key in sorted(translations, key=int):
        text = translations[key]
        if text == "":
            raise CatalogError(f"key {key} 的译文为空")
        if "\r" in text:
            raise CatalogError(f"key {key} 的译文含 CR")
        record = json.dumps(
            {"key": key, "text": text},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        lines.append(record)

    content = "\n".join(lines)
    if lines:
        content += "\n"

    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)
    os.replace(temporary, path)


def accepted_same_source(source: str) -> bool:
    """去掉格式符后没有字母的串，允许译文与原文相同。

    例如 ``100%``、``+ %1HP``、``%1X%.%2Y%`` 都不需要翻译；
    而 ``WAAAGH!`` 含字母，必须显式接受。
    """
    from .text import BR_RE, PLACEHOLDER_RE, has_letters

    residue = PLACEHOLDER_RE.sub("", source)
    residue = BR_RE.sub("", residue)
    return not has_letters(residue)
